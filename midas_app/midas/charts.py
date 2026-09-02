# Copyright (c) 2026, MIDAS and contributors
# For license information, please see license.txt

import math

from markupsafe import Markup

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

DEFAULT_MONTHLY = [
	("Ene", 754866, 71068),
	("Feb", 750877, 75588.5),
	("Mar", 817604, 91005.6),
	("Abr", 677298, 92735.3),
	("May", 586628, 92656.3),
	("Jun", 557666, 82237.3),
	("Jul", 576530, 83974),
	("Ago", 547671, 87364.5),
	("Sep", 599576, 78902.5),
	("Oct", 587840, 70836),
	("Nov", 651685, 63663.5),
	("Dic", 583162, 62461),
]

DEFAULT_HOURLY_CONSUMO = [
	445.979, 451.947, 446.88, 437.727, 444.132, 427.457, 413.21, 1374.62,
	1480.31, 1478.81, 1511.83, 1521.95, 1459.16, 1429.18, 1476.03, 1338.53,
	1200.24, 902.429, 550.964, 479.738, 469.49, 457.169, 459.544, 457.547,
]

DEFAULT_HOURLY_GENERACION = [
	-0.567675, -0.567675, -0.567675, -0.567675, -0.567675, 0.526535, 30.2072, 109.108,
	199.971, 275.42, 329.505, 344.604, 338.063, 310.213, 251.194, 175.722,
	82.6978, 16.9368, -0.344167, -0.567675, -0.567675, -0.567675, -0.567675, -0.567675,
]

DEFAULT_CASH_FLOW = [
	(0, -392238, -392238),
	(1, 124852, -267386),
	(2, 128111, -139274),
	(3, 131453, -7821.45),
	(4, 134879, 127058),
	(5, 138392, 265450),
	(6, 141996, 407446),
	(7, 145691, 553136),
	(8, 149479, 702616),
	(9, 153364, 855979),
	(10, 157346, 1013330),
	(11, 161431, 1174760),
	(12, 165619, 1340380),
	(13, 169914, 1510290),
	(14, 174319, 1684610),
	(15, 178835, 1863440),
	(16, 183465, 2046910),
	(17, 188212, 2235120),
	(18, 193079, 2428200),
	(19, 198070, 2626270),
	(20, 203186, 2829460),
	(21, 208433, 3037890),
	(22, 213812, 3251700),
	(23, 219327, 3471030),
	(24, 224982, 3696010),
	(25, 230780, 3926790),
]

COLORS = ["#1a5276", "#e67e22", "#27ae60", "#c0392b", "#8e44ad", "#16a085"]


def _num(v):
	try:
		return f"{float(v):,.2f}".rstrip("0").rstrip(".")
	except (TypeError, ValueError):
		return str(v)


def _compact(v):
	a = abs(v)
	if a >= 1_000_000:
		return f"{v / 1_000_000:,.1f}M"
	if a >= 1_000:
		return f"{v / 1_000:,.0f}k"
	return f"{v:,.0f}"


def _esc(s):
	return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ticks(minv, maxv, n=5):
	span = maxv - minv
	if span == 0:
		span = 1
	step = span / (n - 1)
	return [minv + step * i for i in range(n)]


def line_chart(title, labels, series, height=260, width=680):
	left, right, top, bottom = 64, 20, 18, 52
	plot_w = width - left - right
	plot_h = height - top - bottom

	all_vals = [v for s in series for v in s["values"] if v is not None]
	if not all_vals:
		return Markup("")

	minv = min(all_vals)
	maxv = max(all_vals)
	if minv == maxv:
		minv -= 1
		maxv += 1
	pad = (maxv - minv) * 0.08
	minv -= pad
	maxv += pad

	def px(i):
		n = len(labels)
		if n <= 1:
			return left + plot_w / 2
		return left + plot_w * i / (n - 1)

	def py(v):
		return top + plot_h - (v - minv) / (maxv - minv) * plot_h

	parts = []

	for t in _ticks(minv, maxv, 5):
		y = py(t)
		parts.append(
			f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
			f'stroke="#e3e6ea" stroke-width="1"/>'
		)
		parts.append(
			f'<text x="{left - 8}" y="{y + 3:.1f}" text-anchor="end" font-size="10" '
			f'fill="#666">{_compact(t)}</text>'
		)

	n = len(labels)
	step_labels = max(1, math.ceil(n / 12))
	for i, lab in enumerate(labels):
		if i % step_labels == 0:
			parts.append(
				f'<text x="{px(i):.1f}" y="{top + plot_h + 16}" text-anchor="middle" '
				f'font-size="10" fill="#666">{_esc(lab)}</text>'
			)

	for idx, s in enumerate(series):
		color = s.get("color") or COLORS[idx % len(COLORS)]
		pts = []
		for i, v in enumerate(s["values"]):
			if v is None:
				continue
			pts.append(f"{px(i):.1f},{py(v):.1f}")
		if pts:
			parts.append(
				f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'
			)
			for p in pts:
				x, y = p.split(",")
				parts.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="{color}"/>')

	legend_y = top + plot_h + 34
	lx = left
	for idx, s in enumerate(series):
		color = s.get("color") or COLORS[idx % len(COLORS)]
		parts.append(f'<rect x="{lx}" y="{legend_y - 8}" width="10" height="10" fill="{color}"/>')
		parts.append(
			f'<text x="{lx + 14}" y="{legend_y}" font-size="10" fill="#444">{_esc(s["name"])}</text>'
		)
		lx += len(s["name"]) * 6.2 + 30

	svg = (
		f'<svg viewBox="0 0 {width} {height}" width="100%" '
		f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'
	)
	return Markup(f'<div class="chart"><div class="chart-title">{_esc(title)}</div>{svg}</div>')


def donut_chart(title, labels, values, height=240, width=680):
	total = sum(values) or 1
	cx, cy, r = 150, 120, 72
	thickness = 26

	start = -math.pi / 2
	parts = []
	for i, v in enumerate(values):
		frac = v / total
		end = start + frac * 2 * math.pi
		color = COLORS[i % len(COLORS)]
		large = 1 if (end - start) > math.pi else 0
		a0 = (cx + r * math.cos(start), cy + r * math.sin(start))
		a1 = (cx + r * math.cos(end), cy + r * math.sin(end))
		parts.append(
			f'<path d="M {a0[0]:.2f} {a0[1]:.2f} A {r} {r} 0 {large} 1 {a1[0]:.2f} {a1[1]:.2f}" '
			f'fill="none" stroke="{color}" stroke-width="{thickness}"/>'
		)
		start = end

	parts.append(
		f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-size="12" fill="#888">Autoconsumo</text>'
	)
	parts.append(
		f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="22" font-weight="bold" '
		f'fill="#333">{_num(values[1])}%</text>'
	)

	lx, ly = 270, 70
	for i, lab in enumerate(labels):
		color = COLORS[i % len(COLORS)]
		parts.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="{color}"/>')
		parts.append(
			f'<text x="{lx + 18}" y="{ly}" font-size="12" fill="#444">'
			f'{_esc(lab)} · {_num(values[i])}%</text>'
		)
		ly += 26

	svg = (
		f'<svg viewBox="0 0 {width} {height}" width="100%" '
		f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'
	)
	return Markup(f'<div class="chart"><div class="chart-title">{_esc(title)}</div>{svg}</div>')


def bar_chart(title, labels, series, height=260, width=680):
	left, right, top, bottom = 64, 20, 18, 56
	plot_w = width - left - right
	plot_h = height - top - bottom

	all_vals = [v for s in series for v in s["values"] if v is not None]
	if not all_vals:
		return Markup("")

	minv = min(min(all_vals), 0)
	maxv = max(all_vals)
	if minv == maxv:
		minv -= 1
		maxv += 1
	pad = (maxv - minv) * 0.08
	maxv += pad
	if minv < 0:
		minv -= pad

	def py(v):
		return top + plot_h - (v - minv) / (maxv - minv) * plot_h

	baseline = py(0)
	parts = []

	for t in _ticks(minv, maxv, 5):
		y = py(t)
		parts.append(
			f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
			f'stroke="#e3e6ea" stroke-width="1"/>'
		)
		parts.append(
			f'<text x="{left - 8}" y="{y + 3:.1f}" text-anchor="end" font-size="10" '
			f'fill="#666">{_compact(t)}</text>'
		)

	n = len(labels)
	n_series = len(series)
	group_w = plot_w / n
	bar_w = group_w / (n_series + 0.6)

	for i in range(n):
		gx = left + group_w * i
		for idx, s in enumerate(series):
			v = s["values"][i]
			if v is None:
				continue
			color = s.get("color") or COLORS[idx % len(COLORS)]
			x = gx + bar_w * idx + bar_w * 0.3
			y1 = py(v)
			parts.append(
				f'<rect x="{x:.1f}" y="{min(y1, baseline):.1f}" width="{bar_w:.1f}" '
				f'height="{max(abs(y1 - baseline), 0.5):.1f}" fill="{color}"/>'
			)

	step_labels = max(1, math.ceil(n / 12))
	for i, lab in enumerate(labels):
		if i % step_labels == 0:
			parts.append(
				f'<text x="{left + group_w * i + group_w / 2:.1f}" y="{top + plot_h + 16}" '
				f'text-anchor="middle" font-size="10" fill="#666">{_esc(lab)}</text>'
			)

	legend_y = top + plot_h + 34
	lx = left
	for idx, s in enumerate(series):
		color = s.get("color") or COLORS[idx % len(COLORS)]
		parts.append(f'<rect x="{lx}" y="{legend_y - 8}" width="10" height="10" fill="{color}"/>')
		parts.append(
			f'<text x="{lx + 14}" y="{legend_y}" font-size="10" fill="#444">{_esc(s["name"])}</text>'
		)
		lx += len(s["name"]) * 6.2 + 30

	svg = (
		f'<svg viewBox="0 0 {width} {height}" width="100%" '
		f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'
	)
	return Markup(f'<div class="chart"><div class="chart-title">{_esc(title)}</div>{svg}</div>')


def pie_chart(title, labels, values, height=240, width=680):
	total = sum(values) or 1
	cx, cy, r = 150, 120, 80

	start = -math.pi / 2
	parts = []
	for i, v in enumerate(values):
		frac = v / total
		if frac <= 0.0001:
			continue
		end = start + frac * 2 * math.pi
		color = COLORS[i % len(COLORS)]
		if frac >= 0.9999:
			parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
		else:
			large = 1 if (end - start) > math.pi else 0
			a0 = (cx + r * math.cos(start), cy + r * math.sin(start))
			a1 = (cx + r * math.cos(end), cy + r * math.sin(end))
			parts.append(
				f'<path d="M {cx} {cy} L {a0[0]:.2f} {a0[1]:.2f} A {r} {r} 0 {large} 1 {a1[0]:.2f} {a1[1]:.2f} Z" '
				f'fill="{color}"/>'
			)
		start = end

	parts.append(
		f'<text x="{cx}" y="{cy - 8}" text-anchor="middle" font-size="12" fill="#888">Autoconsumo</text>'
	)
	parts.append(
		f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="22" font-weight="bold" '
		f'fill="#333">{_num(values[1])}%</text>'
	)

	lx, ly = 270, 70
	for i, lab in enumerate(labels):
		color = COLORS[i % len(COLORS)]
		parts.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" fill="{color}"/>')
		parts.append(
			f'<text x="{lx + 18}" y="{ly}" font-size="12" fill="#444">'
			f'{_esc(lab)} · {_num(values[i])}%</text>'
		)
		ly += 26

	svg = (
		f'<svg viewBox="0 0 {width} {height}" width="100%" '
		f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'
	)
	return Markup(f'<div class="chart"><div class="chart-title">{_esc(title)}</div>{svg}</div>')


def ensure_chart_data(doc):
	if not doc.consumo_mensual:
		for mes, consumo, generacion in DEFAULT_MONTHLY:
			doc.append(
				"consumo_mensual",
				{"mes": mes, "consumo_kwh": consumo, "generacion_kwh": generacion},
			)

	if not doc.perfil_horario:
		for hora in range(24):
			doc.append(
				"perfil_horario",
				{
					"hora": hora,
					"consumo_kw": DEFAULT_HOURLY_CONSUMO[hora],
					"generacion_kw": DEFAULT_HOURLY_GENERACION[hora],
				},
			)

	if not doc.flujo_caja:
		for anio, flujo, acumulado in DEFAULT_CASH_FLOW:
			doc.append(
				"flujo_caja",
				{"anio": anio, "flujo_caja": flujo, "flujo_acumulado": acumulado},
			)


def get_proposal_charts(doc):
	charts = {}

	if doc.consumo_mensual:
		meses = [row.mes for row in doc.consumo_mensual]
		consumo = [row.consumo_kwh or 0 for row in doc.consumo_mensual]
		generacion = [row.generacion_kwh or 0 for row in doc.consumo_mensual]
	else:
		meses = [m for m, _, _ in DEFAULT_MONTHLY]
		consumo = [c for _, c, _ in DEFAULT_MONTHLY]
		generacion = [g for _, _, g in DEFAULT_MONTHLY]

	charts["consumo_generacion"] = bar_chart(
		"Consumo vs Generación (kWh / mes)",
		meses,
		[{"name": "Consumo", "values": consumo}, {"name": "Generación", "values": generacion}],
	)

	coverage = min(max(doc.coverage_pct or 0, 0), 100)
	charts["matriz_energetica"] = pie_chart(
		"Matriz Energética",
		["Consumo anual de ENEE", "Energía Autoconsumida Solar"],
		[100 - coverage, coverage],
	)

	if doc.perfil_horario:
		horas = [str(row.hora) for row in doc.perfil_horario]
		hconsumo = [row.consumo_kw or 0 for row in doc.perfil_horario]
		hgeneracion = [row.generacion_kw or 0 for row in doc.perfil_horario]
	else:
		horas = [str(h) for h in range(24)]
		hconsumo = list(DEFAULT_HOURLY_CONSUMO)
		hgeneracion = list(DEFAULT_HOURLY_GENERACION)

	charts["perfil_horario"] = line_chart(
		"Consumo Promedio por Hora (kW)",
		horas,
		[{"name": "Consumo (kW)", "values": hconsumo}, {"name": "Generación (kW)", "values": hgeneracion}],
	)

	if doc.flujo_caja:
		anios = [str(row.anio) for row in doc.flujo_caja]
		flujo = [row.flujo_caja or 0 for row in doc.flujo_caja]
		acumulado = [row.flujo_acumulado or 0 for row in doc.flujo_caja]
	else:
		anios = [str(a) for a, _, _ in DEFAULT_CASH_FLOW]
		flujo = [f for _, f, _ in DEFAULT_CASH_FLOW]
		acumulado = [acc for _, _, acc in DEFAULT_CASH_FLOW]

	charts["flujo_caja"] = bar_chart(
		"Flujo de Caja (USD / año)",
		anios,
		[{"name": "After-tax cash flow", "values": flujo}],
	)
	charts["flujo_acumulado"] = bar_chart(
		"Flujo de Caja Acumulado (USD / año)",
		anios,
		[{"name": "Cumulative payback", "values": acumulado}],
	)

	energy_cost = doc.energy_cost or 0.1457
	if doc.consumo_mensual:
		sin_ssfv = [(row.consumo_kwh or 0) * energy_cost for row in doc.consumo_mensual]
		con_ssfv = [
			max((row.consumo_kwh or 0) - (row.generacion_kwh or 0), 0) * energy_cost
			for row in doc.consumo_mensual
		]
	else:
		sin_ssfv = [c * energy_cost for _, c, _ in DEFAULT_MONTHLY]
		con_ssfv = [max(c - g, 0) * energy_cost for _, c, g in DEFAULT_MONTHLY]

	charts["consumo_antes_despues"] = bar_chart(
		"Consumo Antes y Después del SSFV ($ / mes)",
		meses,
		[{"name": "Sin SSFV", "values": sin_ssfv}, {"name": "Con SSFV", "values": con_ssfv}],
	)

	return charts
