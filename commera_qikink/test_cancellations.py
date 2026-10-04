import frappe
from frappe.tests import IntegrationTestCase

from commera_qikink.cancellations import mark_cancelled_on_qikink
from commera_qikink.purchase_orders import get_purchase_orders, make_drop_ship_order
from commera_qikink.test_order_status import make_order, make_sent_order


class TestCancelSentOrder(IntegrationTestCase):
	def setUp(self):
		self.sales_order = make_sent_order()
		self.purchase_order = make_drop_ship_order(self.sales_order)
		if not self.purchase_order:
			self.skipTest("No buying price for the Qikink item on the settings' buying price list")

	def cancel_order(self):
		sales_order = frappe.get_doc("Sales Order", self.sales_order.name)
		# As Commera's storefront cancel does, so a shopper reaches before_cancel.
		sales_order.flags.ignore_permissions = True
		sales_order.cancel()

	def test_a_sent_order_refuses_to_cancel(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Cancel it on the Qikink dashboard first"):
			self.cancel_order()

		self.assertEqual(frappe.db.get_value("Sales Order", self.sales_order.name, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Purchase Order", self.purchase_order, "docstatus"), 1)

	def test_a_shopper_is_told_to_contact_the_store(self):
		with self.set_user("Guest"), self.assertRaisesRegex(frappe.ValidationError, "Contact the store"):
			self.cancel_order()

	def test_marking_it_cancelled_on_qikink_cancels_the_purchase_order_and_allows_the_cancel(self):
		mark_cancelled_on_qikink(self.sales_order.name)

		self.assertEqual(
			frappe.db.get_value("Sales Order", self.sales_order.name, "commera_qikink_status"), "Cancelled"
		)
		self.assertEqual(frappe.db.get_value("Purchase Order", self.purchase_order, "docstatus"), 2)
		self.assertEqual(get_purchase_orders(self.sales_order.name), [])

		self.cancel_order()
		self.assertEqual(frappe.db.get_value("Sales Order", self.sales_order.name, "docstatus"), 2)

	def test_qikinks_own_cancelled_status_cancels_the_purchase_order_with_the_order(self):
		self.sales_order.db_set("commera_qikink_status", "Cancelled")

		self.cancel_order()
		self.assertEqual(frappe.db.get_value("Purchase Order", self.purchase_order, "docstatus"), 2)

	def test_a_delivered_order_cannot_be_marked_cancelled(self):
		self.sales_order.db_set("commera_qikink_status", "Delivered")

		with self.assertRaisesRegex(frappe.ValidationError, "not an open Qikink order"):
			mark_cancelled_on_qikink(self.sales_order.name)


class TestCancelUnsentOrder(IntegrationTestCase):
	def test_an_unsent_order_cancels_freely(self):
		sales_order = make_order()
		sales_order.cancel()
		self.assertEqual(frappe.db.get_value("Sales Order", sales_order.name, "docstatus"), 2)
