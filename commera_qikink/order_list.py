import frappe
from frappe.query_builder import functions
from frappe.utils.data import cint
from pypika import analytics

MAX_PAGE_LENGTH = 100


def get_sent_orders(start: int = 0, page_length: int = 20) -> dict:
	sales_order = frappe.qb.DocType("Sales Order")
	purchase_order_item = frappe.qb.DocType("Purchase Order Item")
	query = (
		frappe.qb.from_(sales_order)
		.left_join(purchase_order_item)
		.on((purchase_order_item.sales_order == sales_order.name) & (purchase_order_item.docstatus == 1))
		.select(
			sales_order.name,
			sales_order.customer_name,
			sales_order.commera_qikink_order_number.as_("order_number"),
			sales_order.commera_qikink_status.as_("status"),
			functions.Max(purchase_order_item.parent).as_("purchase_order"),
			sales_order.commera_qikink_sent_at.as_("sent_on"),
			analytics.Count("*").over().as_("total"),
		)
		.where((sales_order.docstatus == 1) & (sales_order.commera_qikink_order_number.isnotnull()))
		.where(sales_order.commera_qikink_order_number != "")
		.groupby(sales_order.name)
		.orderby(sales_order.creation, order=frappe.qb.desc)
		.limit(min(cint(page_length) or 20, MAX_PAGE_LENGTH))
		.offset(cint(start))
	)
	if "bwh_shipping" in frappe.get_installed_apps():
		shipping_request = frappe.qb.DocType("Shipping Request")
		query = (
			query.left_join(shipping_request)
			.on(
				(shipping_request.ref_doctype == "Sales Order")
				& (shipping_request.ref_docname == sales_order.name)
				& (shipping_request.docstatus < 2)
			)
			.select(functions.Max(shipping_request.status).as_("shipment_status"))
		)

	rows = query.run(as_dict=True)
	total = rows[0].total if rows else 0
	for row in rows:
		row.pop("total")
	return {"rows": rows, "total": total}
