import frappe
from commera.sdk import as_plugin_user
from commera.sdk import orders as commera_orders
from frappe import _
from frappe.utils.data import cstr

from commera_qikink.client import Qikink, get_order_number
from commera_qikink.purchase_orders import deliver_drop_ship_order

# 10 orders a page: 20 pages a run stays well inside Qikink's 30 requests a minute.
MAX_SYNC_PAGES = 20
SAVEPOINT = "commera_qikink_status"
FINAL_STATUSES = {"delivered", "returned", "partially returned", "cancelled", "archived", "lost"}
# Qikink's courier statuses as Shipping Request statuses; any other status that comes with an AWB is Ready To Ship.
SHIPMENT_STATUSES = {
	"picked up": "In Transit",
	"in-transit": "In Transit",
	"delivery rescheduled": "In Transit",
	"misrouted": "In Transit",
	"oda": "In Transit",
	"self collect": "In Transit",
	"exception": "In Transit",
	"out for delivery": "Out For Delivery",
	"not attempted": "Undelivered",
	"consignee unavailable": "Undelivered",
	"residence / office closed": "Undelivered",
	"otp not shared": "Undelivered",
	"otp verification cancelled": "Undelivered",
	"incorrect/incomplete address": "Undelivered",
	"maximum attempts reached": "Undelivered",
	"refused to accept": "Undelivered",
	"open delivery refused": "Undelivered",
	"delivered": "Delivered",
	"rto initiated": "RTO",
	"reverse pickup initiated": "RTO",
	"returned": "RTO",
	"partially returned": "RTO",
	"lost": "Lost",
}


def sync_open_orders() -> list[str]:
	if open_orders := get_open_orders():
		return sync_orders(open_orders, isolate_errors=True)
	return []


def refresh_order_status(sales_order: str) -> str:
	order_number, status = frappe.db.get_value(
		"Sales Order", sales_order, ["commera_qikink_order_number", "commera_qikink_status"]
	)
	if not order_number:
		frappe.throw(_("Order {0} has not been sent to Qikink.").format(sales_order))
	if is_final_status(status):
		return status
	if not sync_orders({order_number: sales_order}):
		frappe.throw(
			_("Qikink does not list order {0} among its {1} most recent orders.").format(
				order_number, MAX_SYNC_PAGES * 10
			)
		)
	return frappe.db.get_value("Sales Order", sales_order, "commera_qikink_status")


def is_final_status(status: str | None) -> bool:
	return cstr(status).casefold() in FINAL_STATUSES


def get_open_orders() -> dict[str, str]:
	rows = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "commera_qikink_order_number": ["is", "set"]},
		fields=["name", "commera_qikink_order_number", "commera_qikink_status"],
	)
	return {
		row.commera_qikink_order_number: row.name
		for row in rows
		if not is_final_status(row.commera_qikink_status)
	}


def sync_orders(open_orders: dict[str, str], isolate_errors: bool = False) -> list[str]:
	"""Takes {Qikink order number: Sales Order}; returns the Sales Orders Qikink listed."""
	pending = dict(open_orders)
	synced = []
	for qikink_order in Qikink().iter_orders(MAX_SYNC_PAGES):
		if sales_order := pending.pop(get_order_number(qikink_order), None):
			if isolate_errors:
				save_order_or_log(sales_order, qikink_order)
			else:
				save_order(sales_order, qikink_order)
			synced.append(sales_order)
		if not pending:
			break
	return synced


def save_order_or_log(sales_order: str, qikink_order: dict):
	frappe.db.savepoint(SAVEPOINT)
	try:
		save_order(sales_order, qikink_order)
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(
			title=_("Qikink status sync failed for {0}").format(sales_order),
			reference_doctype="Sales Order",
			reference_name=sales_order,
		)


def save_order(sales_order: str, qikink_order: dict):
	status = cstr(qikink_order.get("status")).strip()
	if status:
		frappe.db.set_value(
			"Sales Order", sales_order, "commera_qikink_status", status, update_modified=False
		)

	shipping = qikink_order.get("shipping") or {}
	if awb := cstr(shipping.get("awb")).strip():
		with as_plugin_user("commera_qikink"):
			commera_orders.record_shipment(
				sales_order,
				awb=awb,
				carrier=cstr(shipping.get("courier_provider_name")).strip() or None,
				tracking_url=cstr(shipping.get("tracking_link")).strip() or None,
				status=SHIPMENT_STATUSES.get(status.casefold(), "Ready To Ship"),
			)

	if status.casefold() == "delivered":
		deliver_drop_ship_order(sales_order)
