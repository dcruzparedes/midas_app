import frappe


def execute():
	from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons_from_installed_apps

	if frappe.db.exists("Desktop Icon", "MIDAS-GDP"):
		return

	create_desktop_icons_from_installed_apps()