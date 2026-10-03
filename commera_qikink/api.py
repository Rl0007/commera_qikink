import frappe
from commera.sdk import STORE_ORDER_TYPE
from frappe.utils import today

from commera_qikink import products


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
