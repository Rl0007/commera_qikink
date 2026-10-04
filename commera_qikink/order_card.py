import frappe

from commera_qikink.orders import has_qikink_lines


def get_order_card(sales_order: str) -> dict:
	order_number, status = frappe.db.get_value(
		"Sales Order", sales_order, ["commera_qikink_order_number", "commera_qikink_status"]
	)
	return {
		"has_qikink_lines": has_qikink_lines(sales_order),
		"order_number": order_number,
		"status": status if order_number else None,
		"purchase_orders": get_purchase_orders(sales_order),
		"shipments": get_shipments(sales_order),
	}


def get_purchase_orders(sales_order: str) -> list[str]:
	return frappe.get_all(
		"Purchase Order Item",
		filters={"sales_order": sales_order, "docstatus": 1},
		pluck="parent",
		distinct=True,
		order_by="parent",
	)


def get_shipments(sales_order: str) -> list[dict]:
	# Qikink's AWB lives on the order's Shipping Request (commera.sdk.orders.record_shipment), not on the order.
	if "bwh_shipping" not in frappe.get_installed_apps():
		return []
	return frappe.get_all(
		"Shipping Request",
		filters={"ref_doctype": "Sales Order", "ref_docname": sales_order, "docstatus": ["<", 2]},
		fields=["name", "awb", "carrier", "status", "tracking_url"],
		order_by="creation",
	)
