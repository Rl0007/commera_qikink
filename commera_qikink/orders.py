import re

import frappe
from commera.sdk import orders as commera_orders
from frappe import _
from frappe.utils.data import cint, cstr, flt, now_datetime

from commera_qikink.client import Qikink, QikinkError
from commera_qikink.items import get_qikink_items
from commera_qikink.purchase_orders import make_drop_ship_order

COD_PAYMENT_MODE = "COD"
MAX_ORDER_NUMBER_LENGTH = 15
MAX_ADDRESS_LINE_LENGTH = 90
SENDING_STATUS = "Sending"
SENT_STATUS = "Sent"
CANCELLED_STATUS = "Cancelled"
PURCHASE_ORDER_SAVEPOINT = "commera_qikink_purchase_order"


def on_order_paid(event):
	# A COD order fires order_paid once its cash is collected; staff send those with "Send to Qikink".
	if event.data.get("payment_mode") == COD_PAYMENT_MODE:
		return
	send_order(event.sales_order)


def send_order(sales_order: str) -> str | None:
	"""Returns the Qikink order number, or None when the order has no Qikink lines. Also makes the
	drop-ship Purchase Order, so calling it again retries one that failed."""
	# Locks the row, so the paid event and a staff click can't both get past the sent check.
	order = frappe.get_doc("Sales Order", sales_order, for_update=True)
	if order.docstatus != 1:
		frappe.throw(_("Submit order {0} before sending it to Qikink.").format(sales_order))
	if not order.commera_qikink_order_number:
		lines = get_qikink_lines(order)
		if not lines:
			return None
		submit_to_qikink(order, lines)

	save_drop_ship_order(order)
	return order.commera_qikink_order_number


def set_drop_ship_lines(doc, method=None):
	# Commera maps cart lines to the order with delivered_by_supplier 0, and it can't change after submit.
	if doc.docstatus != 0:
		return
	qikink_items = get_qikink_items([row.item_code for row in doc.items])
	supplier = frappe.db.get_single_value("Qikink Settings", "supplier")
	for row in doc.items:
		if row.item_code in qikink_items:
			row.delivered_by_supplier = 1
			row.supplier = supplier


def has_qikink_lines(sales_order: str) -> bool:
	item_codes = frappe.get_all("Sales Order Item", filters={"parent": sales_order}, pluck="item_code")
	return bool(get_qikink_items(item_codes))


def get_qikink_lines(order) -> list[tuple]:
	qikink_items = get_qikink_items([row.item_code for row in order.items])
	lines = [(row, qikink_items[row.item_code]) for row in order.items if row.item_code in qikink_items]
	if unmapped := sorted({row.item_name for row, item in lines if not item.commera_qikink_sku}):
		frappe.throw(
			_("Add a Qikink SKU to {0} before sending this order to Qikink.").format(", ".join(unmapped))
		)
	return lines


def submit_to_qikink(order, lines: list[tuple]):
	order_number = get_order_number(order.name)
	payload = get_order_payload(order, lines, order_number)
	client = Qikink()
	if not (order.commera_qikink_status == SENDING_STATUS and client.find_order(order_number)):
		order.db_set("commera_qikink_status", SENDING_STATUS, update_modified=False)
		# Committed before the call, so a retry after a crash looks for the order before sending it again.
		frappe.db.commit()
		create_order(client, payload)

	order.db_set(
		{
			"commera_qikink_order_number": order_number,
			"commera_qikink_status": SENT_STATUS,
			"commera_qikink_sent_at": now_datetime(),
		},
		update_modified=False,
	)
	frappe.db.commit()


def save_drop_ship_order(order):
	frappe.db.savepoint(PURCHASE_ORDER_SAVEPOINT)
	try:
		make_drop_ship_order(order)
	except Exception:
		# Qikink already holds the order, so a failed purchase order is logged, never allowed to undo it.
		frappe.db.rollback(save_point=PURCHASE_ORDER_SAVEPOINT)
		frappe.log_error(
			title=_("Qikink purchase order failed for {0}").format(order.name),
			reference_doctype="Sales Order",
			reference_name=order.name,
		)


def create_order(client: Qikink, payload: dict):
	try:
		client.create_order(payload)
	except QikinkError as error:
		# Qikink refuses a number it already holds, which is a retry of an order it accepted.
		if "duplicate order" not in cstr(error).lower() or not client.find_order(payload["order_number"]):
			raise


def get_order_number(sales_order: str) -> str:
	"""SAL-ORD-2026-00062 becomes 202600062: Qikink takes at most 15 of a-z, 0-9 and _."""
	order_number = re.sub(r"\D", "", cstr(sales_order))
	if not order_number:
		frappe.throw(_("Order {0} has no digits to use as a Qikink order number.").format(sales_order))
	if len(order_number) > MAX_ORDER_NUMBER_LENGTH:
		frappe.throw(
			_("A Qikink order number has at most {0} digits, and order {1} gives {2}.").format(
				MAX_ORDER_NUMBER_LENGTH, sales_order, order_number
			)
		)
	return order_number


def get_order_payload(order, lines: list[tuple], order_number: str) -> dict:
	commera_order = commera_orders.get_order(order.name)
	return {
		"order_number": order_number,
		"qikink_shipping": 1,
		"gateway": get_gateway(commera_order),
		"total_order_value": get_order_value(order, lines),
		"line_items": [get_line_item(row, item) for row, item in lines],
		"shipping_address": get_shipping_address(commera_order),
	}


def get_order_value(order, lines: list[tuple]) -> float:
	"""What the shopper paid for the Qikink lines alone, which is what Qikink's courier collects on COD:
	their net amount (after any order discount, before tax) plus their share of every percentage tax,
	whether included in the price or added on top. "Actual" rows (shipping, COD fee, app fees such as
	gift wrap) are charges on the whole order, so they stay with the store."""
	line_rows = {row.name for row, _item in lines}
	tax_rows = {tax.name for tax in order.taxes if tax.charge_type != "Actual"}
	tax_share = sum(
		flt(detail.amount)
		for detail in order.item_wise_tax_details
		if detail.item_row in line_rows and detail.tax_row in tax_rows
	)
	net_amount = sum(flt(row.net_amount) for row, _item in lines)
	return flt(net_amount + tax_share, order.precision("grand_total"))


def get_gateway(order: dict) -> str:
	# Qikink's courier collects the cash only when told COD; once Commera records the cash, it is prepaid.
	return "COD" if order["payment_mode"] == COD_PAYMENT_MODE and not order["is_paid"] else "Prepaid"


def get_line_item(row, item) -> dict:
	line_item = {"sku": item.commera_qikink_sku, "quantity": cint(row.qty), "price": flt(row.rate)}
	if item.commera_qikink_plain_product:
		# A blank catalog product: print type 1 and no designs is how Qikink reads "plain".
		return {"search_from_my_products": 0, "print_type_id": 1, **line_item}
	# Qikink rejects print_type_id and designs here; it reads both from the merchant's My Products.
	return {"search_from_my_products": 1, **line_item}


def get_shipping_address(order: dict) -> dict:
	address = order["shipping_address"]
	if not address:
		frappe.throw(_("Order {0} has no shipping address to send to Qikink.").format(order["name"]))

	first_name, _space, last_name = cstr(order["customer_name"]).strip().partition(" ")
	address1, address2 = split_address_line(
		cstr(address["address_line1"]).strip(), cstr(address["address_line2"]).strip()
	)
	shipping_address = {
		"first_name": first_name,
		"last_name": last_name.strip(),
		"address1": address1,
		"address2": address2,
		"phone": cstr(address["phone"] or order["phone"]).strip(),
		"email": cstr(order["email"]).strip(),
		"city": cstr(address["city"]).strip(),
		"zip": cstr(address["pincode"]).strip(),
		"province": cstr(address["state"]).strip(),
		"country_code": cstr(frappe.get_cached_value("Country", address["country"], "code")).upper(),
	}
	optional_fields = ("last_name", "address2")
	if missing := [
		field for field, value in shipping_address.items() if not value and field not in optional_fields
	]:
		frappe.throw(
			_("The shipping address of order {0} is missing {1}, which Qikink needs.").format(
				order["name"], ", ".join(missing)
			)
		)
	return shipping_address


def split_address_line(line1: str, line2: str) -> tuple[str, str]:
	# Qikink takes 90 characters in address1; the rest moves to address2 at a word break.
	if len(line1) <= MAX_ADDRESS_LINE_LENGTH:
		return line1, line2
	cut = line1.rfind(" ", 0, MAX_ADDRESS_LINE_LENGTH + 1)
	cut = cut if cut > 0 else MAX_ADDRESS_LINE_LENGTH
	return line1[:cut].strip(), f"{line1[cut:].strip()} {line2}".strip()
