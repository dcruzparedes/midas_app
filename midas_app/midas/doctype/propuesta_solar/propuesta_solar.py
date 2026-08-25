# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEPARTMENT_KWH_PER_KWP = {
    "Atlántida": 1476.927,
    "Choluteca": 1573.376,
    "Colón": 1431.085,
    "Comayagua": 1413.753,
    "Copán": 1493.467,
    "Cortés": 1380.0,
    "El Paraíso": 1485.507,
    "Francisco Morazán": 1472.774,
    "Gracias a Dios": 1360.772,
    "Intibucá": 1494.827,
    "Islas de la Bahía": 1528.053,
    "La Paz": 1489.717,
    "Lempira": 1523.294,
    "Ocotepeque": 1547.3,
    "Olancho": 1413.302,
    "Santa Bárbara": 1422.78,
    "Valle": 1567.319,
    "Yoro": 1411.618,
}

TARIFF_USD_PER_KWH = {
    "Residencial": 0.213871,
    "Baja Tensión": 0.214389,
    "Media Tensión": 0.137515,
    "Alta Tensión": 0.129485,
}

DC_TO_AC_RATIO = 1.25


class PropuestaSolar(Document):
    def validate(self):
        self.calculate()

    def calculate(self):
        kwh_per_kwp = DEPARTMENT_KWH_PER_KWP.get(self.project_department) or 0
        tariff_usd = TARIFF_USD_PER_KWH.get(self.tariff_type) or 0

        monthly = self.monthly_consumption or 0
        savings = self.desired_savings or 0

        dc_power = 0.0
        if kwh_per_kwp and monthly and savings:
            dc_power = monthly * 12 / kwh_per_kwp * savings / 100

        self.dc_power = dc_power
        self.ac_power = dc_power / DC_TO_AC_RATIO if dc_power else 0.0
        self.energy_generated = dc_power * kwh_per_kwp if dc_power else 0.0

        if self.energy_generated and self.annual_consumption:
            self.coverage_pct = self.energy_generated / self.annual_consumption * 100
        else:
            self.coverage_pct = 0.0

        self.annual_savings_usd = self.energy_generated * tariff_usd
        self.investment_cost = dc_power * (self.panel_price or 0) * 1000

        if dc_power:
            self.unit_cost = self.investment_cost / (dc_power * 1000)
        else:
            self.unit_cost = self.panel_price or 0

        if self.annual_savings_usd:
            self.payback_period = self.investment_cost / self.annual_savings_usd
        else:
            self.payback_period = 0.0

        if self.panel_power and dc_power:
            self.panel_quantity = round(dc_power * 1000 / self.panel_power)
            self.required_area = dc_power * 1000 / self.panel_power * (self.panel_size or 0)
        else:
            self.panel_quantity = 0
            self.required_area = 0.0

        if self.om_annual_unit and dc_power:
            self.om_annual_total = self.om_annual_unit * dc_power
        elif not self.om_annual_total:
            self.om_annual_total = 0


@frappe.whitelist()
def get_quotation_data(quotation_name):
    """Devuelve los datos clave de una cotización para poblar la propuesta."""
    quotation = frappe.get_doc("Quotation", quotation_name)

    fields = [
        "proposal_date",
        "project_location",
        "project_department",
        "tariff_type",
        "voltage_type",
        "commissioning_months",
        "monthly_consumption",
        "annual_consumption",
        "peak_demand",
        "desired_savings",
        "panel_power",
        "panel_size",
        "panel_price",
    ]

    data = {field: quotation.get(field) for field in fields}
    data["customer"] = quotation.party_name
    data["customer_name"] = quotation.customer_name

    return data
