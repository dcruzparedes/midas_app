# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.model.document import Document

from midas_app.midas.charts import ensure_chart_data, get_proposal_charts
from midas_app.midas.solar_calc import compute_solar_metrics


class PropuestaSolar(Document):
	def validate(self):
		if not self.energy_cost:
			self.energy_cost = 0.1457
		self.calculate()

	def calculate(self):
		compute_solar_metrics(self)
		self.calculate_equipment_power()

		if self.dc_power:
			self.unit_cost = self.investment_cost / (self.dc_power * 1000)
		else:
			self.unit_cost = self.panel_price or 0

		if self.om_annual_unit and self.dc_power:
			self.om_annual_total = self.om_annual_unit * self.dc_power
		elif not self.om_annual_total:
			self.om_annual_total = 0

		ensure_chart_data(self)
		self.update_cash_flow()
		self.update_payment_terms()

	def update_payment_terms(self):
		total = self.total_project_price or 0
		self.payment_acceptance_amount = total * 0.5
		self.payment_reception_amount = total * 0.5

	def calculate_equipment_power(self):
		for row in self.equipment:
			divisor = 1000 if row.unit in ("W", "Wp") else 1
			row.total_power = ((row.quantity or 0) * (row.unit_power or 0)) / divisor

	def update_cash_flow(self):
		running = 0.0
		for row in self.flujo_caja:
			running += row.flujo_caja or 0
			row.flujo_acumulado = running

	def get_charts(self):
		return get_proposal_charts(self)


@frappe.whitelist()
def get_quotation_data(quotation_name):
	"""Devuelve los datos clave de una cotización para poblar la propuesta."""
	quotation = frappe.get_doc("Cotizacion Midas", quotation_name)

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
	data["customer"] = quotation.customer
	data["customer_name"] = quotation.customer_name

	return data


def get_proposal_html(name):
	doc = frappe.get_doc("Propuesta Solar", name)
	print_format = frappe.get_doc("Print Format", "Propuesta Solar")
	return frappe.render_template(print_format.html, frappe._dict({"doc": doc, "frappe": frappe}))


def _resolve_image_path(src):
	import os

	from urllib.parse import urlparse

	if src.startswith(("http://", "https://")):
		src = urlparse(src).path
	if src.startswith("/assets/"):
		rest = src.replace("/assets/", "", 1)
		app, _, sub = rest.partition("/")
		candidate = os.path.join(frappe.get_site_path("assets"), app, sub)
		if os.path.exists(candidate):
			return os.path.abspath(candidate)
		return os.path.join(frappe.get_app_path(app), "public", sub)
	if src.startswith("/private/files/"):
		return os.path.abspath(os.path.join(frappe.get_site_path("private", "files"), src.replace("/private/files/", "")))
	if src.startswith("/files/"):
		return os.path.abspath(os.path.join(frappe.get_site_path("public", "files"), src.replace("/files/", "")))
	return src


def _data_uri_to_file(src, tmpdir):
	import base64
	import os

	header, _, b64 = src.partition(",")
	mime = header.split(";")[0].split(":")[1] if ":" in header else "image/png"
	ext = mime.split("/")[-1].split("+")[0] or "png"
	path = os.path.join(tmpdir, f"img.{ext}")
	with open(path, "wb") as f:
		f.write(base64.b64decode(b64))
	return path


def _prepare_html(html):
	import os
	import tempfile

	from bs4 import BeautifulSoup

	soup = BeautifulSoup(html, "html.parser")
	tmpdir = tempfile.mkdtemp(prefix="midas_export_")

	for img in soup.find_all("img"):
		src = img.get("src") or ""
		if src.startswith("data:"):
			local = _data_uri_to_file(src, tmpdir)
			if local:
				img["src"] = local
			continue
		local = _resolve_image_path(src)
		if local and os.path.exists(local):
			img["src"] = local

	return str(soup)


def _fmt_num(value, digits=2):
	try:
		return f"{float(value or 0):,.{digits}f}"
	except (TypeError, ValueError):
		return str(value or "")


def _chart_png(chart_html, tmpdir, name):
	import cairosvg

	from bs4 import BeautifulSoup

	soup = BeautifulSoup(str(chart_html), "xml")
	svg = soup.find("svg")
	title_tag = soup.find(class_="chart-title")
	title = title_tag.get_text(strip=True) if title_tag else ""
	if svg is None:
		return None, title
	path = os.path.join(tmpdir, f"chart_{name}.png")
	parts = [float(x) for x in (svg.get("viewBox", "0 0 680 260").split())]
	vw, vh = (parts[2], parts[3]) if len(parts) == 4 else (680, 260)
	scale = 1600 / (vw or 680)
	cairosvg.svg2png(
		bytestring=str(svg).encode("utf-8"),
		write_to=path,
		output_width=int(vw * scale),
		output_height=int(vh * scale),
	)
	return path, title


def _add_floating_logo(paragraph, path, width, page_width):
	import copy

	from docx.oxml import parse_xml
	from docx.oxml.ns import nsdecls, qn
	from docx.shared import Inches

	run = paragraph.add_run()
	run.add_picture(path, width=width)

	drawing = run._r.find(qn("w:drawing"))
	inline = drawing.find(qn("wp:inline"))
	if inline is None:
		return

	extent = copy.deepcopy(inline.find(qn("wp:extent")))
	effect_extent = copy.deepcopy(inline.find(qn("wp:effectExtent")))
	doc_pr = copy.deepcopy(inline.find(qn("wp:docPr")))
	c_nv = copy.deepcopy(inline.find(qn("wp:cNvGraphicFramePr")))
	graphic = copy.deepcopy(inline.find(qn("a:graphic")))

	gap = int(Inches(0.2))
	pos_h = int(page_width) - int(width) - gap
	pos_v = gap

	anchor = parse_xml(
		'<wp:anchor %s distT="0" distB="0" distL="0" distR="0" simplePos="0" '
		'relativeHeight="0" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
		'<wp:simplePos x="0" y="0"/>'
		'<wp:positionH relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionH>'
		'<wp:positionV relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionV>'
		'</wp:anchor>' % (nsdecls("wp"), pos_h, pos_v)
	)
	anchor.append(extent)
	if effect_extent is not None:
		anchor.append(effect_extent)
	anchor.append(parse_xml('<wp:wrapNone %s/>' % nsdecls("wp")))
	anchor.append(doc_pr)
	anchor.append(c_nv)
	anchor.append(graphic)
	inline.addnext(anchor)
	inline.getparent().remove(inline)


def _build_proposal_docx(doc):
	import io
	import os
	import tempfile

	from docx import Document
	from docx.enum.table import WD_ALIGN_VERTICAL
	from docx.enum.text import WD_ALIGN_PARAGRAPH
	from docx.oxml import parse_xml
	from docx.oxml.ns import nsdecls
	from docx.shared import Inches, Pt, RGBColor

	NAVY = RGBColor(0x1A, 0x52, 0x76)
	HEADER_FILL = "EEF2F6"

	document = Document()
	sec = document.sections[0]
	sec.left_margin = sec.right_margin = Inches(0.75)
	sec.top_margin = sec.bottom_margin = Inches(0.6)
	document.styles["Normal"].font.name = "Calibri"
	document.styles["Normal"].font.size = Pt(11)

	tmpdir = tempfile.mkdtemp(prefix="midas_docx_")

	def shade(cell, fill):
		cell._tc.get_or_add_tcPr().append(
			parse_xml(r'<w:shd {} w:val="clear" w:color="auto" w:fill="{}"/>'.format(nsdecls("w"), fill))
		)

	def heading(text):
		p = document.add_paragraph()
		run = p.add_run(text)
		run.font.size = Pt(14)
		run.font.bold = True
		run.font.color.rgb = NAVY
		p._p.get_or_add_pPr().append(
			parse_xml(
				r'<w:pBdr {}><w:bottom w:val="single" w:sz="8" w:space="1" w:color="1A5276"/></w:pBdr>'.format(
					nsdecls("w")
				)
			)
		)
		p.paragraph_format.space_after = Pt(6)
		return p

	def centered(text, size, bold=False, color=None, italic=False, space_after=4):
		p = document.add_paragraph()
		p.alignment = WD_ALIGN_PARAGRAPH.CENTER
		run = p.add_run(text)
		run.font.size = Pt(size)
		run.font.bold = bold
		run.font.italic = italic
		if color:
			run.font.color.rgb = color
		p.paragraph_format.space_after = Pt(space_after)
		return p

	def body(text, space_after=6):
		p = document.add_paragraph(text)
		p.paragraph_format.space_after = Pt(space_after)
		return p

	def kv_table(rows):
		table = document.add_table(rows=0, cols=2, style="Table Grid")
		table.autofit = False
		for k, v in rows:
			row = table.add_row()
			c1, c2 = row.cells
			c1.width = Inches(3.1)
			c2.width = Inches(3.6)
			p1 = c1.paragraphs[0]
			r1 = p1.add_run(str(k))
			r1.font.bold = True
			r1.font.color.rgb = NAVY
			p2 = c2.paragraphs[0]
			r2 = p2.add_run(str(v if v is not None else ""))
			r2.font.size = Pt(11)
		document.add_paragraph().paragraph_format.space_after = Pt(2)
		return table

	def bullets(text):
		for line in (text or "").splitlines():
			if line.strip():
				document.add_paragraph(line.strip(), style="List Bullet")

	def add_charts(keys):
		charts = doc.get_charts()
		for key in keys:
			path, title = _chart_png(charts.get(key, ""), tmpdir, key)
			if not path:
				continue
			centered(title, 12, bold=True, color=NAVY, space_after=2)
			p = document.add_paragraph()
			p.alignment = WD_ALIGN_PARAGRAPH.CENTER
			p.add_run().add_picture(path, width=Inches(6.9))
			document.add_paragraph().paragraph_format.space_after = Pt(2)

	# ---- Logo flotante en la esquina superior derecha de la primera página ----
	logo = _resolve_image_path("/assets/midas_app/images/logo_midas.jpg")

	title_p = centered("Corporación Midas", 22, bold=True, color=NAVY, space_after=0)
	if logo and os.path.exists(logo):
		_add_floating_logo(title_p, logo, Inches(1.2), sec.page_width)
	centered("Soluciones Solares Fotovoltaicas — Modelo EPC", 11, italic=True, space_after=8)
	centered("CARTA DE PRESENTACIÓN", 15, bold=True, space_after=10)

	kv_table(
		[
			("Cliente", doc.customer_name),
			(
				"Ubicación",
				((doc.project_location or "") + (", " + doc.project_department if doc.project_department else "")).strip(" ,"),
			),
			("Fecha", doc.get_formatted("proposal_date")),
		]
	)

	body(
		"Por medio de la presente, nos complace presentar a Corporación Midas, una empresa especializada "
		"en el desarrollo integral de proyectos solares fotovoltaicos bajo el modelo EPC (Ingeniería, Procura "
		"y Construcción). Nos dirigimos a usted con el objetivo de ofrecerle una solución energética sostenible, "
		"eficiente y adaptada a las necesidades específicas de su empresa."
	)
	body("Se detalla a continuación las características principales del sistema fotovoltaico propuesto:")

	heading("Características Principales del Sistema")
	kv_table(
		[
			("Capacidad del sistema", f"{_fmt_num(doc.dc_power)} kWp"),
			("Potencia en inversores", f"{_fmt_num(doc.ac_power)} kWac"),
			("Energía Generada", f"{_fmt_num(doc.energy_generated)} kWh"),
			("% de energía ahorrada al año", f"{_fmt_num(doc.coverage_pct)}%"),
			("Valor de la inversión (USD)", doc.get_formatted("investment_cost")),
			("Periodo de recuperación", f"{_fmt_num(doc.payback_period)} años"),
			(
				"Puesta en marcha",
				f"{(doc.commissioning_months or 0)} mes(es) después de aceptación de oferta",
			),
		]
	)

	heading("Implantación del Proyecto")
	body(
		"Como parte del proceso de evaluación energética y con el objetivo de identificar oportunidades de ahorro "
		"y sostenibilidad, se presenta a continuación una propuesta preliminar para la implantación del sistema "
		f"solar fotovoltaico mencionado en las instalaciones de {doc.customer_name or ''}"
		f"{' en ' + doc.project_location if doc.project_location else ''}"
		f"{', ' + doc.project_department if doc.project_department else ''}."
	)

	heading("Equipos Principales del Sistema")
	for e in doc.equipment:
		table = document.add_table(rows=1, cols=2, style="Table Grid")
		table.autofit = False
		img_cell, spec_cell = table.rows[0].cells
		img_cell.width = Inches(2.6)
		spec_cell.width = Inches(4.1)
		img_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
		img_ok = False
		if e.image:
			ipath = _resolve_image_path(e.image)
			if ipath and os.path.exists(ipath):
				ip = img_cell.paragraphs[0]
				ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
				ip.add_run().add_picture(ipath, width=Inches(2.4))
				img_ok = True
		if not img_ok:
			ip = img_cell.paragraphs[0]
			ip.alignment = WD_ALIGN_PARAGRAPH.CENTER
			ir = ip.add_run("Sin imagen")
			ir.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
			ir.font.size = Pt(10)

		specs = [
			("Tipo de Equipo", e.equipment_type),
			("Marca", e.marca),
			("Modelo", e.model),
			("Cantidad", f"{e.quantity or 0:,.0f}"),
			("Potencia Unitaria", f"{_fmt_num(e.unit_power)} {e.unit or ''}".strip()),
			("Potencia Total", f"{_fmt_num(e.total_power)} {e.unit or ''}".strip()),
			("Voltaje", e.voltage),
		]
		for i, (k, v) in enumerate(specs):
			p = spec_cell.paragraphs[0] if i == 0 else spec_cell.add_paragraph()
			r1 = p.add_run(f"{k}: ")
			r1.font.bold = True
			r1.font.color.rgb = NAVY
			r1.font.size = Pt(10.5)
			r2 = p.add_run(str(v or ""))
			r2.font.size = Pt(10.5)
			p.paragraph_format.space_after = Pt(1)
		document.add_paragraph().paragraph_format.space_after = Pt(2)

	if not doc.equipment:
		body("Sin equipos registrados.")

	heading("Resultados Técnicos del Análisis")
	body("Comportamiento Energético del Sistema", space_after=3)
	kv_table(
		[
			("Potencia", f"{_fmt_num(doc.dc_power)} kWp"),
			("Potencia Nominal", f"{_fmt_num(doc.ac_power)} kWac"),
			("Consumo anual", f"{_fmt_num(doc.annual_consumption)} kWh"),
			("Energía Generada anual (1er año)", f"{_fmt_num(doc.energy_generated)} kWh"),
			("Energía Inyectada", f"{_fmt_num(doc.energy_injected)} kWh"),
			("Energía Autoconsumida", f"{_fmt_num(doc.energy_self_consumed)} kWh"),
			("% de cobertura", f"{_fmt_num(doc.coverage_pct)}%"),
			("% de inyección a red", f"{_fmt_num(doc.injection_pct)}%"),
		]
	)
	body("Datos del Cliente", space_after=3)
	kv_table(
		[
			("Consumo Anual", f"{_fmt_num(doc.annual_consumption)} kWh"),
			("Consumo promedio mensual", f"{_fmt_num(doc.monthly_consumption)} kWh"),
			("Pico de demanda", f"{_fmt_num(doc.peak_demand)} kW"),
			("Tarifa", doc.tariff_type),
		]
	)

	heading("Gráficas Técnicas")
	add_charts(["consumo_generacion", "matriz_energetica", "perfil_horario"])

	heading("Resultados Financieros del Análisis")
	body("Resumen Económico", space_after=3)
	kv_table(
		[
			("Costo Unitario", f"{_fmt_num(doc.unit_cost, 3)} $/Wp"),
			("Costo Total de la inversión", doc.get_formatted("investment_cost")),
			("Ahorro neto (1er año)", doc.get_formatted("annual_savings_usd")),
			("Valor presente Neto (VPN)", doc.get_formatted("npv")),
			("Periodo de Repago", f"{_fmt_num(doc.payback_period)} años"),
			("Periodo de análisis", f"{doc.analysis_period or 25} años"),
			("Tasa Interna de Retorno", f"{_fmt_num(doc.irr)}%"),
		]
	)
	body("Consideraciones Financieras", space_after=3)
	kv_table(
		[
			("Intereses", f"{_fmt_num(doc.interest_rate)}%"),
			("Inflación", f"{_fmt_num(doc.inflation)}%"),
			("Costo de la energía", f"{_fmt_num(doc.energy_cost, 4)} $/kWh"),
			("O&M anual unitario", f"{_fmt_num(doc.om_annual_unit)} $/kWp"),
			("Costo total de O&M anual", doc.get_formatted("om_annual_total")),
			("Periodo de análisis", "30 años"),
		]
	)

	heading("Gráficas Financieras")
	add_charts(["flujo_caja", "consumo_antes_despues", "flujo_acumulado"])

	heading("Entregables del Proyecto")
	bullets(doc.deliverables)

	heading("Garantías de Componentes")
	bullets(doc.warranties)

	heading("Consideraciones")
	bullets(doc.considerations)

	heading("Exclusiones")
	bullets(doc.exclusions)

	if doc.total_project_price:
		heading("Condiciones de Pago y Aceptación de Oferta")

		box = document.add_table(rows=0, cols=2)
		box.autofit = True

		title_row = box.add_row()
		title_cell = title_row.cells[0].merge(title_row.cells[1])
		shade(title_cell, "1A5276")
		tp = title_cell.paragraphs[0]
		tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
		run = tp.add_run("CONDICIONES DE PAGO")
		run.font.bold = True
		run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
		run.font.size = Pt(12)

		total_row = box.add_row()
		total_cell = total_row.cells[0].merge(total_row.cells[1])
		tp = total_cell.paragraphs[0]
		tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
		r = tp.add_run("Precio Total del Proyecto:  ")
		r.font.size = Pt(12)
		r2 = tp.add_run(doc.get_formatted("total_project_price"))
		r2.font.bold = True
		r2.font.size = Pt(16)
		r2.font.color.rgb = NAVY

		amounts_row = box.add_row()
		labels = ["50% AL ACEPTAR LA OFERTA", "50% RECEPCIÓN DEL PROYECTO"]
		amounts = [
			doc.get_formatted("payment_acceptance_amount"),
			doc.get_formatted("payment_reception_amount"),
		]
		for i, cell in enumerate(amounts_row.cells):
			pc = cell.paragraphs[0]
			pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
			run = pc.add_run(labels[i])
			run.font.bold = True
			run.font.color.rgb = NAVY
			run.font.size = Pt(10)
			pc2 = cell.add_paragraph()
			pc2.alignment = WD_ALIGN_PARAGRAPH.CENTER
			run2 = pc2.add_run(amounts[i])
			run2.font.bold = True
			run2.font.size = Pt(16)
			run2.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)

		box._tbl.tblPr.append(
			parse_xml(
				'<w:tblBorders {}>'
				'<w:top w:val="single" w:sz="12" w:space="0" w:color="1A5276"/>'
				'<w:left w:val="single" w:sz="12" w:space="0" w:color="1A5276"/>'
				'<w:bottom w:val="single" w:sz="12" w:space="0" w:color="1A5276"/>'
				'<w:right w:val="single" w:sz="12" w:space="0" w:color="1A5276"/>'
				'<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
				'<w:insideV w:val="single" w:sz="6" w:space="0" w:color="C9D6E2"/>'
				'</w:tblBorders>'.format(nsdecls("w"))
			)
		)

		document.add_paragraph().paragraph_format.space_after = Pt(2)

	if doc.payment_conditions:
		bullets(doc.payment_conditions)

	document.add_paragraph().paragraph_format.space_after = Pt(40)
	sig = document.add_table(rows=1, cols=2)
	sig.autofit = True
	signers = [("Gerente General", "Corporación Midas"), ("Gerente General", doc.customer_name or "")]
	for i, (role, who) in enumerate(signers):
		cell = sig.rows[0].cells[i]
		cell.width = Inches(3.4)

		line_p = cell.paragraphs[0]
		line_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
		line_p.paragraph_format.left_indent = Inches(0.5)
		line_p.paragraph_format.right_indent = Inches(0.5)
		line_p.paragraph_format.space_after = Pt(4)
		lr = line_p.add_run(" ")
		lr.font.size = Pt(6)
		line_p._p.get_or_add_pPr().append(
			parse_xml(
				r'<w:pBdr {}><w:bottom w:val="single" w:sz="8" w:space="1" w:color="000000"/></w:pBdr>'.format(
					nsdecls("w")
				)
			)
		)

		name_p = cell.add_paragraph()
		name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
		r1 = name_p.add_run(role)
		r1.font.bold = True
		r1.font.size = Pt(11)
		r1.add_break()
		r2 = name_p.add_run(who)
		r2.font.bold = True
		r2.font.size = Pt(11)

	bio = io.BytesIO()
	document.save(bio)
	return bio.getvalue()


@frappe.whitelist()
def download_proposal_pdf(name):
	"""Descarga la propuesta en PDF (generado con WeasyPrint)."""
	from weasyprint import HTML

	html = _prepare_html(get_proposal_html(name))
	pdf = HTML(string=html, base_url="/").write_pdf()
	frappe.local.response.filename = f"Propuesta-{name.replace(' ', '-')}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def download_proposal_word(name):
	"""Descarga la propuesta en Word (.docx editable y con formato)."""
	doc = frappe.get_doc("Propuesta Solar", name)
	docx_bytes = _build_proposal_docx(doc)
	frappe.local.response.filename = f"Propuesta-{name.replace(' ', '-')}.docx"
	frappe.local.response.filecontent = docx_bytes
	frappe.local.response.type = "download"
