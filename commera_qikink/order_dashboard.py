import frappe
from frappe import _
from frappe.query_builder import functions
from frappe.utils.data import add_days, add_months, cint, cstr, flt, formatdate, get_first_day, getdate

from commera_qikink import order_list
from commera_qikink.items import get_qikink_items
from commera_qikink.order_status import FINAL_STATUSES, SHIPMENT_STATUSES, is_final_status
from commera_qikink.orders import SENDING_STATUS

# All time mirrors Commera's reports, which look back 36 months.
PERIODS = {
	"Last 7 days": ("day", 7),
	"Last 30 days": ("day", 30),
	"Last 12 months": ("month", 12),
	"All time": ("month", 36),
}
DELIVERED_STATUS = "delivered"
ARCHIVED_STATUS = "archived"
PROBLEM_SHIPMENT_STATUSES = {"RTO", "Undelivered", "Lost"}
PROBLEM_STATUSES = (FINAL_STATUSES - {DELIVERED_STATUS, ARCHIVED_STATUS}) | {
	status
	for status, shipment_status in SHIPMENT_STATUSES.items()
	if shipment_status in PROBLEM_SHIPMENT_STATUSES
}
CLOSED_ORDER_STATUSES = ("Closed", "Completed")
RECENT_ORDERS = 5
MAX_NEEDS_ATTENTION = 8


def get_dashboard(period: str) -> dict:
	if period not in PERIODS:
		frappe.throw(_("Pick one of {0}.").format(", ".join(PERIODS)))
	unit, length = PERIODS[period]
	from_date = get_period_start(unit, length)
	rows = get_sent_rows(from_date)
	needs_attention = get_unsent_orders() + get_problem_orders(from_date)
	return {
		"stats": get_stats(rows),
		"buckets": get_buckets(unit, length, rows),
		"by_status": get_by_status(rows),
		"needs_attention": needs_attention[:MAX_NEEDS_ATTENTION],
		"needs_attention_total": len(needs_attention),
		"recent": order_list.get_sent_orders(0, RECENT_ORDERS)["rows"],
	}


def get_period_start(unit: str, length: int):
	today = getdate()
	if unit == "day":
		return add_days(today, -(length - 1))
	return get_first_day(add_months(today, -(length - 1)))


def get_stage(status: str | None) -> str | None:
	status = cstr(status).casefold()
	if status == DELIVERED_STATUS:
		return "delivered"
	if status in PROBLEM_STATUSES:
		return "problems"
	if is_final_status(status):
		return None
	return "in_progress"


def get_sent_rows(from_date) -> list[dict]:
	sales_order = frappe.qb.DocType("Sales Order")
	sent_on = functions.Date(sales_order.commera_qikink_sent_at)
	return (
		frappe.qb.from_(sales_order)
		.select(
			sent_on.as_("sent_on"),
			sales_order.commera_qikink_status.as_("status"),
			functions.Count("*").as_("count"),
			functions.Sum(sales_order.base_grand_total).as_("value"),
		)
		.where((sales_order.docstatus == 1) & (sales_order.commera_qikink_order_number.isnotnull()))
		.where(sales_order.commera_qikink_order_number != "")
		.where(sales_order.commera_qikink_sent_at >= from_date)
		.groupby(sent_on, sales_order.commera_qikink_status)
		.run(as_dict=True)
	)


def get_stats(rows: list[dict]) -> dict:
	stats = {"sent": 0, "value": 0.0, "delivered": 0, "in_progress": 0, "problems": 0}
	for row in rows:
		stats["sent"] += cint(row.count)
		stats["value"] += flt(row.value)
		if stage := get_stage(row.status):
			stats[stage] += cint(row.count)
	return stats


def get_buckets(unit: str, length: int, rows: list[dict]) -> list[dict]:
	start = get_period_start(unit, length)
	counts = {}
	for row in rows:
		key = get_bucket_key(unit, row.sent_on)
		counts[key] = counts.get(key, 0) + cint(row.count)

	if unit == "day":
		dates = [add_days(start, offset) for offset in range(length)]
		label_format = "d MMM"
	else:
		dates = [add_months(start, offset) for offset in range(length)]
		label_format = "MMM yy"
	return [
		{
			"key": get_bucket_key(unit, date),
			"label": formatdate(date, label_format),
			"count": counts.get(get_bucket_key(unit, date), 0),
		}
		for date in dates
	]


def get_bucket_key(unit: str, date) -> str:
	return getdate(date).strftime("%Y-%m-%d" if unit == "day" else "%Y-%m")


def get_by_status(rows: list[dict]) -> list[dict]:
	counts = {}
	for row in rows:
		counts[row.status] = counts.get(row.status, 0) + cint(row.count)
	return sorted(
		({"status": status, "count": count, "stage": get_stage(status)} for status, count in counts.items()),
		key=lambda row: (-row["count"], cstr(row["status"])),
	)


def get_unsent_orders() -> list[dict]:
	sales_order = frappe.qb.DocType("Sales Order")
	sales_order_item = frappe.qb.DocType("Sales Order Item")
	rows = (
		frappe.qb.from_(sales_order)
		.join(sales_order_item)
		.on(sales_order_item.parent == sales_order.name)
		.select(
			sales_order.name,
			sales_order.customer_name,
			sales_order.commera_qikink_status.as_("status"),
			sales_order_item.item_code,
		)
		.distinct()
		.where((sales_order.docstatus == 1) & sales_order.status.notin(CLOSED_ORDER_STATUSES))
		.where(
			sales_order.commera_qikink_order_number.isnull() | (sales_order.commera_qikink_order_number == "")
		)
		.where(sales_order_item.delivered_by_supplier == 1)
		.orderby(sales_order.creation, order=frappe.qb.desc)
		.run(as_dict=True)
	)
	qikink_items = get_qikink_items(list({row.item_code for row in rows}))
	orders = {}
	for row in rows:
		if row.item_code in qikink_items and row.name not in orders:
			orders[row.name] = {
				"name": row.name,
				"customer_name": row.customer_name,
				"kind": "unsent",
				"reason": _("Sending did not finish")
				if row.status == SENDING_STATUS
				else _("Not sent to Qikink"),
			}
	return list(orders.values())


def get_problem_orders(from_date) -> list[dict]:
	sales_order = frappe.qb.DocType("Sales Order")
	rows = (
		frappe.qb.from_(sales_order)
		.select(
			sales_order.name,
			sales_order.customer_name,
			sales_order.commera_qikink_status.as_("status"),
		)
		.where((sales_order.docstatus == 1) & (sales_order.commera_qikink_order_number.isnotnull()))
		.where(sales_order.commera_qikink_order_number != "")
		.where(sales_order.commera_qikink_sent_at >= from_date)
		.where(functions.Lower(sales_order.commera_qikink_status).isin(list(PROBLEM_STATUSES)))
		.orderby(sales_order.commera_qikink_sent_at, order=frappe.qb.desc)
		.run(as_dict=True)
	)
	return [
		{
			"name": row.name,
			"customer_name": row.customer_name,
			"kind": "problem",
			"reason": row.status,
		}
		for row in rows
	]
