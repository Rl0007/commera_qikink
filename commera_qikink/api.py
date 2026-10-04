import frappe
from commera.sdk import STORE_ORDER_TYPE
from frappe import _
from frappe.utils import today

from commera_qikink import order_card, order_status, orders, products


@frappe.whitelist()
def get_summary() -> dict:
	frappe.has_permission("Sales Order", "read", throw=True)
	return {
		"orders_today": frappe.db.count(
			"Sales Order",
			{"order_type": STORE_ORDER_TYPE, "transaction_date": today(), "docstatus": ("<", 2)},
		)
	}


@frappe.whitelist(methods=["GET"])
def get_product_skus(item: str) -> list[dict]:
	frappe.has_permission("Item", "read", doc=item, throw=True)
	return products.get_product_skus(item)


@frappe.whitelist(methods=["POST"])
def save_product_skus(item: str, skus: str | list) -> list[dict]:
	frappe.has_permission("Item", "write", doc=item, throw=True)
	return products.save_product_skus(item, frappe.parse_json(skus))


@frappe.whitelist(methods=["GET"])
def get_order_card(sales_order: str) -> dict:
	frappe.has_permission("Sales Order", "read", doc=sales_order, throw=True)
	return order_card.get_order_card(sales_order)


@frappe.whitelist(methods=["POST"])
def send_order(name: str) -> str:
	frappe.has_permission("Sales Order", "write", doc=name, throw=True)
	order_number = orders.send_order(name)
	if not order_number:
		frappe.throw(_("Order {0} has no Qikink items to send.").format(name))
	return _("Sent to Qikink as order {0}").format(order_number)


@frappe.whitelist(methods=["POST"])
def refresh_order_status(name: str) -> str:
	frappe.has_permission("Sales Order", "write", doc=name, throw=True)
	return _("Qikink status: {0}").format(order_status.refresh_order_status(name))
