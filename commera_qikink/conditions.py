import frappe


def can_edit_item(doctype: str, name: str) -> bool:
	return bool(frappe.has_permission("Item", "write", name))
