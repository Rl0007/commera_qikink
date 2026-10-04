import frappe
from commera.sdk import as_apps_user
from frappe import _
from frappe.utils import today

try:
	from erpnext.selling.doctype.sales_order.mapper import make_purchase_order
except ImportError:
	from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order


def make_drop_ship_order(order) -> str | None:
	"""Buys the order's Qikink lines from Qikink with a submitted Purchase Order. Safe to call again."""
	# Locks the order again: send_order committed after Qikink accepted, which released its lock.
	frappe.db.get_value("Sales Order", order.name, "name", for_update=True)
	settings = frappe.get_cached_doc("Qikink Settings")
	lines = get_unordered_lines(order, settings.supplier)
	if not lines:
		return None

	rates = get_buying_rates([row.item_code for row in lines], settings.buying_price_list)
	if missing := sorted({row.item_code for row in lines if row.item_code not in rates}):
		frappe.log_error(
			title=_("Qikink purchase order not made for {0}").format(order.name),
			message=_("No buying price on price list {0} for {1}. Add it, then send the order again.").format(
				settings.buying_price_list or _("(not set in Qikink Settings)"), ", ".join(missing)
			),
			reference_doctype="Sales Order",
			reference_name=order.name,
		)
		return None

	# The staff member who clicks Send may sell without being allowed to buy.
	with as_apps_user("commera_qikink"):
		selected_items = [{"item_code": row.item_code, "supplier": settings.supplier} for row in lines]
		# Commera orders carry no delivery date, which the mapper copies into each line's Required By.
		target = frappe.new_doc("Purchase Order", schedule_date=order.delivery_date or today())
		purchase_order = make_purchase_order(order.name, selected_items, target)[0]
		purchase_order.buying_price_list = settings.buying_price_list
		for item in purchase_order.items:
			item.price_list_rate = item.rate = rates[item.item_code]
		purchase_order.save()
		purchase_order.submit()
	return purchase_order.name


def get_unordered_lines(order, supplier: str) -> list:
	lines = [
		row for row in order.items if supplier and row.delivered_by_supplier and row.supplier == supplier
	]
	if not lines:
		return []
	ordered = set(
		frappe.get_all(
			"Purchase Order Item",
			filters={"sales_order_item": ["in", [row.name for row in lines]], "docstatus": ["<", 2]},
			pluck="sales_order_item",
		)
	)
	return [row for row in lines if row.name not in ordered]


def get_buying_rates(item_codes: list[str], price_list: str | None) -> dict:
	if not price_list:
		return {}
	prices = frappe.get_all(
		"Item Price",
		filters={"price_list": price_list, "item_code": ["in", item_codes]},
		fields=["item_code", "price_list_rate"],
	)
	return {price.item_code: price.price_list_rate for price in prices}
