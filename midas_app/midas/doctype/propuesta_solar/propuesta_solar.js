// Copyright (c) 2026, MIDAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Propuesta Solar", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.quotation) {
			frm.add_custom_button(__("Traer datos de cotización"), () => {
				load_quotation_data(frm);
			});
		}
	},
	quotation(frm) {
		if (frm.doc.quotation) {
			load_quotation_data(frm);
		}
	},
});

frappe.ui.form.on("Propuesta Equipo", {
	quantity(frm, cdt, cdn) {
		recalculate_total_power(frm, cdt, cdn);
	},
	unit_power(frm, cdt, cdn) {
		recalculate_total_power(frm, cdt, cdn);
	},
	unit(frm, cdt, cdn) {
		recalculate_total_power(frm, cdt, cdn);
	},
});

function load_quotation_data(frm) {
	frappe.call({
		method: "midas_app.midas.doctype.propuesta_solar.propuesta_solar.get_quotation_data",
		args: { quotation_name: frm.doc.quotation },
		callback(r) {
			if (r.message) {
				Object.entries(r.message).forEach(([field, value]) => {
					if (field === "customer" || field === "customer_name") {
						return;
					}
					if (value !== undefined && value !== null) {
						frm.set_value(field, value);
					}
				});
			}
		},
	});
}

function recalculate_total_power(frm, cdt, cdn) {
	const row = frappe.get_doc(cdt, cdn);
	const divisor = row.unit === "W" || row.unit === "Wp" ? 1000 : 1;
	const total = ((row.quantity || 0) * (row.unit_power || 0)) / divisor;
	frappe.model.set_value(cdt, cdn, "total_power", total);
}
