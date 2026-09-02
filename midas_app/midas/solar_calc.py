# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

DEPARTMENT_KWH_PER_KWP = {
	"Atlántida": 1476.9268425890157,
	"Choluteca": 1573.3757376350386,
	"Colón": 1431.0852393067894,
	"Comayagua": 1413.7530756598037,
	"Copán": 1493.4665849662317,
	"Cortés": 1380.0,
	"El Paraíso": 1485.5069201156239,
	"Francisco Morazán": 1472.7743450485921,
	"Gracias a Dios": 1360.7718026934501,
	"Intibucá": 1494.82689720398,
	"Islas de la Bahía": 1528.0534427408718,
	"La Paz": 1489.7165350135203,
	"Lempira": 1523.2936629514536,
	"Ocotepeque": 1547.3000226452291,
	"Olancho": 1413.3020740365787,
	"Santa Bárbara": 1422.7802442259422,
	"Valle": 1567.3186716574974,
	"Yoro": 1411.6180682287434,
}

TARIFF_LPS_PER_KWH = {
	"Residencial": 5.7372,
	"Baja Tensión": 5.7511,
	"Media Tensión": 3.6889,
	"Alta Tensión": 3.4735,
}

TARIFF_USD_PER_KWH = {
	"Residencial": 0.21387113008145231,
	"Baja Tensión": 0.21438929376898846,
	"Media Tensión": 0.13751467819798324,
	"Alta Tensión": 0.1294850049393301,
}

DC_TO_AC_RATIO = 1.25
EXCHANGE_RATE = 26.8255


def compute_solar_metrics(doc):
	kwh_per_kwp = DEPARTMENT_KWH_PER_KWP.get(doc.project_department) or 0
	tariff_usd = TARIFF_USD_PER_KWH.get(doc.tariff_type) or 0

	monthly = doc.monthly_consumption or 0
	savings = doc.desired_savings or 0

	dc_power = 0.0
	if kwh_per_kwp and monthly and savings:
		dc_power = monthly * 12 / kwh_per_kwp * savings / 100

	doc.dc_power = dc_power
	doc.ac_power = dc_power / DC_TO_AC_RATIO if dc_power else 0.0
	doc.energy_generated = dc_power * kwh_per_kwp if dc_power else 0.0

	if doc.energy_generated and doc.annual_consumption:
		doc.coverage_pct = doc.energy_generated / doc.annual_consumption * 100
	else:
		doc.coverage_pct = 0.0

	doc.annual_savings_usd = doc.energy_generated * tariff_usd
	doc.investment_cost = dc_power * (doc.panel_price or 0) * 1000

	if doc.annual_savings_usd:
		doc.payback_period = doc.investment_cost / doc.annual_savings_usd
	else:
		doc.payback_period = 0.0

	if doc.panel_power and dc_power:
		doc.panel_quantity = round(dc_power * 1000 / doc.panel_power)
		doc.required_area = dc_power * 1000 / doc.panel_power * (doc.panel_size or 0)
	else:
		doc.panel_quantity = 0
		doc.required_area = 0.0
