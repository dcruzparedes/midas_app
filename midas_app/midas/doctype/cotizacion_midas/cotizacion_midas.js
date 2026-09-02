// Copyright (c) 2026, MIDAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cotizacion Midas", {
	refresh(frm) {
		if (!frm.is_new() && !frm.doc.propuesta) {
			frm.add_custom_button(__("Generar Propuesta Midas"), () => {
				frappe.new_doc("Propuesta Solar", { quotation: frm.doc.name });
			});
		}
	},
	additional_discount_percentage(frm) {
		recalc_taxes(frm);
	},
});

frappe.ui.form.on("Cotizacion Midas Item", {
	item_code(frm, cdt, cdn) {
		load_item_details(frm, cdt, cdn);
	},
	qty(frm, cdt, cdn) {
		recalc_row(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		recalc_row(frm, cdt, cdn);
	},
	discount_percentage(frm, cdt, cdn) {
		recalc_row(frm, cdt, cdn);
	},
	discount_amount(frm, cdt, cdn) {
		recalc_row(frm, cdt, cdn);
	},
});

frappe.ui.form.on("Cotizacion Midas Tax", {
	charge_type(frm, cdt, cdn) {
		recalc_taxes(frm);
	},
	rate(frm, cdt, cdn) {
		recalc_taxes(frm);
	},
	tax_amount(frm, cdt, cdn) {
		recalc_taxes(frm);
	},
});

function load_item_details(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	if (!row.item_code) {
		return;
	}
	frappe.call({
		method: "midas_app.midas.doctype.cotizacion_midas.cotizacion_midas.get_item_details",
		args: { item_code: row.item_code },
		callback(r) {
			if (r.message) {
				frappe.model.set_value(cdt, cdn, "item_name", r.message.item_name);
				frappe.model.set_value(cdt, cdn, "description", r.message.description);
				if (r.message.rate && !row.rate) {
					frappe.model.set_value(cdt, cdn, "rate", r.message.rate);
				}
			}
		},
	});
}

function recalc_row(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const rate = row.rate || 0;
	const qty = row.qty || 0;
	const pct = row.discount_percentage || 0;
	const amt = row.discount_amount || 0;
	const net_rate = Math.max(rate - (rate * pct) / 100 - amt, 0);

	frappe.model.set_value(cdt, cdn, "net_rate", net_rate);
	frappe.model.set_value(cdt, cdn, "amount", qty * rate);
	frappe.model.set_value(cdt, cdn, "net_amount", qty * net_rate);
	recalc_totals(frm);
}

function recalc_totals(frm) {
	let total_qty = 0;
	let base_total = 0;
	let total = 0;

	(frm.doc.items || []).forEach((row) => {
		total_qty += row.qty || 0;
		base_total += row.amount || 0;
		total += row.net_amount || 0;
	});

	frm.set_value("total_qty", total_qty);
	frm.set_value("base_total", base_total);
	frm.set_value("total", total);
	recalc_taxes(frm);
}

function recalc_taxes(frm) {
	const total = frm.doc.total || 0;
	const pct = frm.doc.additional_discount_percentage || 0;
	const discount_amount = (total * pct) / 100;
	const net_total = total - discount_amount;

	frm.set_value("discount_amount", discount_amount);
	frm.set_value("net_total", net_total);

	let total_taxes = 0;
	(frm.doc.taxes || []).forEach((row) => {
		let amount = row.tax_amount || 0;
		if (row.charge_type === "Sobre Total Neto") {
			amount = (net_total * (row.rate || 0)) / 100;
			frappe.model.set_value("Cotizacion Midas Tax", row.name, "tax_amount", amount);
		}
		total_taxes += amount;
	});

	const grand_total = net_total + total_taxes;
	frm.set_value("total_taxes_and_charges", total_taxes);
	frm.set_value("grand_total", grand_total);
	frm.set_value("rounded_total", Math.round(grand_total * 100) / 100);
}
