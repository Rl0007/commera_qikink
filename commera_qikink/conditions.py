import frappe

from commera_qikink.cancellations import can_mark_cancelled
from commera_qikink.orders import has_qikink_lines


def can_edit_item(doctype: str, name: str) -> bool:
	return bool(frappe.has_permission("Item", "write", name))


def can_send_order(doctype: str, name: str) -> bool:
	order = frappe.db.get_value(
		"Sales Order", name, ["docstatus", "commera_qikink_order_number"], as_dict=True
	)
	return bool(
		order
		and order.docstatus == 1
		and not order.commera_qikink_order_number
		and frappe.has_permission("Sales Order", "write", name)
		and has_qikink_lines(name)
	)


def is_sent_order(doctype: str, name: str) -> bool:
	return bool(frappe.db.get_value("Sales Order", name, "commera_qikink_order_number"))


def can_mark_cancelled_on_qikink(doctype: str, name: str) -> bool:
	order = frappe.db.get_value(
		"Sales Order",
		name,
		["docstatus", "commera_qikink_order_number", "commera_qikink_status"],
		as_dict=True,
	)
	return bool(order and can_mark_cancelled(order) and frappe.has_permission("Sales Order", "cancel", name))
