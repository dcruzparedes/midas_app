import frappe


def execute():
    frappe.delete_doc("DocType", "Propuesta Solar Test", ignore_missing=True, force=True)
