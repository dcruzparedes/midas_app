# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from midas_app.midas.solar_calc import compute_solar_metrics


class CotizacionMidas(Document):
	def validate(self):
		self.calculate()

	def calculate(self):
		compute_solar_metrics(self)
		self.calculate_item_totals()
		self.calculate_taxes_and_totals()

	def calculate_item_totals(self):
		total_qty = 0.0
		base_total = 0.0
		total = 0.0

		for item in self.items:
			item.qty = item.qty or 0
			item.rate = item.rate or 0
			item.discount_percentage = item.discount_percentage or 0
			item.discount_amount = item.discount_amount or 0

			discount_from_pct = item.rate * item.discount_percentage / 100
			item.net_rate = max(item.rate - discount_from_pct - item.discount_amount, 0)
			item.amount = item.qty * item.rate
			item.net_amount = item.qty * item.net_rate

			total_qty += item.qty
			base_total += item.amount
			total += item.net_amount

		self.total_qty = total_qty
		self.base_total = base_total
		self.total = total

	def calculate_taxes_and_totals(self):
		total = self.total or 0
		additional_discount_pct = self.additional_discount_percentage or 0

		self.discount_amount = total * additional_discount_pct / 100
		net_total = total - self.discount_amount
		self.net_total = net_total

		total_taxes = 0.0
		for tax in self.taxes:
			if tax.charge_type == "Sobre Total Neto":
				tax.tax_amount = net_total * (tax.rate or 0) / 100
			else:
				tax.tax_amount = tax.tax_amount or 0
			total_taxes += tax.tax_amount

		self.total_taxes_and_charges = total_taxes
		self.grand_total = net_total + total_taxes
		self.rounded_total = round(self.grand_total, 2)


@frappe.whitelist()
def get_item_details(item_code):
	servicio = frappe.get_cached_doc("Servicio", item_code)
	return {
		"item_name": servicio.nombre,
		"description": servicio.descripcion,
		"rate": servicio.precio,
	}
