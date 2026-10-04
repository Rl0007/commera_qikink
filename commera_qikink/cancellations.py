import frappe
from frappe import _
from frappe.utils.data import cstr

from commera_qikink.order_status import is_final_status
from commera_qikink.orders import CANCELLED_STATUS
from commera_qikink.purchase_orders import cancel_drop_ship_order


def validate_cancel(doc, method=None):
	# Qikink has no cancel API: an order it holds is printed and shipped unless staff cancel it on Qikink.
	if not doc.commera_qikink_order_number:
		return
	if is_cancelled_on_qikink(doc.commera_qikink_status):
		cancel_drop_ship_order(doc.name)
		return
	if frappe.has_permission("Sales Order", "cancel", doc=doc):
		frappe.throw(
			_(
				"Qikink is printing this order as Qikink order {0}, and it can't be cancelled from here. "
				"Cancel it on the Qikink dashboard first, then use Mark cancelled on Qikink on this order."
			).format(doc.commera_qikink_order_number),
			title=_("Cancel it on Qikink first"),
		)
	frappe.throw(
		_("This order is already being printed and can't be cancelled here. Contact the store."),
		title=_("Order can't be cancelled"),
	)


def mark_cancelled_on_qikink(sales_order: str):
	order = frappe.get_doc("Sales Order", sales_order, for_update=True)
	if not can_mark_cancelled(order):
		frappe.throw(_("Order {0} is not an open Qikink order.").format(sales_order))
	cancel_drop_ship_order(sales_order)
	order.db_set("commera_qikink_status", CANCELLED_STATUS, update_modified=False)
	order.add_comment("Info", _("Marked cancelled on Qikink"))


def can_mark_cancelled(order) -> bool:
	return bool(
		order.docstatus == 1
		and order.commera_qikink_order_number
		and not is_final_status(order.commera_qikink_status)
	)


def is_cancelled_on_qikink(status: str | None) -> bool:
	return cstr(status).casefold() == CANCELLED_STATUS.casefold()
