# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PropuestaEquipo(Document):
	pass


@frappe.whitelist()
def get_item_details(item_code):
	equipo = frappe.get_cached_doc("Equipo", item_code)
	return {"item_name": equipo.nombre}
