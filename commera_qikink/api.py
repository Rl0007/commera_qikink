import frappe
from frappe import _

from commera_qikink import order_card, order_list, order_status, orders, products


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


@frappe.whitelist(methods=["GET"])
def get_sent_orders(start: int = 0, page_length: int = 20) -> dict:
	frappe.has_permission("Sales Order", "read", throw=True)
	return order_list.get_sent_orders(start, page_length)


@frappe.whitelist(methods=["POST"])
def sync_open_orders() -> str:
	frappe.has_permission("Sales Order", "write", throw=True)
	return _("Updated {0} orders from Qikink").format(len(order_status.sync_open_orders()))
