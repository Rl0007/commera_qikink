from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from commera_qikink import orders
from commera_qikink.cart import get_unmapped_item_refusal
from commera_qikink.client import Qikink
from commera_qikink.items import get_qikink_items
from commera_qikink.test_order_status import make_order


class TestSendOrder(IntegrationTestCase):
	def setUp(self):
		self.sales_order = make_order()
		self.order_number = orders.get_order_number(self.sales_order.name)
		self.qikink_orders = []
		self.created = []
		self.create_reply = {"order_id": 1, "number": f"654367_{self.order_number}"}
		patchers = (
			patch("commera_qikink.client.make_get_request", side_effect=self.fake_get),
			patch("commera_qikink.client.make_post_request", side_effect=self.fake_post),
			patch.object(Qikink, "get_token", return_value="test-token"),
			# send_order commits around the Qikink call; the test's rows must still roll back.
			patch.object(frappe.db, "commit"),
		)
		for patcher in patchers:
			patcher.start()
			self.addCleanup(patcher.stop)

	def fake_get(self, url, headers=None, params=None):
		return self.qikink_orders if params.get("page_no") == 1 else []

	def fake_post(self, url, headers=None, json=None, data=None):
		self.created.append(json)
		return self.create_reply

	def get_qikink_fields(self):
		return frappe.db.get_value(
			"Sales Order",
			self.sales_order.name,
			["commera_qikink_order_number", "commera_qikink_status"],
		)

	def get_sent_at(self):
		return frappe.db.get_value("Sales Order", self.sales_order.name, "commera_qikink_sent_at")

	def test_an_order_is_sent_once(self):
		self.assertEqual(orders.send_order(self.sales_order.name), self.order_number)
		self.assertEqual(orders.send_order(self.sales_order.name), self.order_number)

		self.assertEqual(len(self.created), 1)
		payload = self.created[0]
		self.assertEqual(payload["order_number"], self.order_number)
		self.assertTrue(all(line["sku"] for line in payload["line_items"]))
		self.assertEqual(self.get_qikink_fields(), (self.order_number, orders.SENT_STATUS))
		self.assertIsNotNone(self.get_sent_at())

	def test_a_mixed_order_sends_only_the_qikink_lines_value(self):
		store_item = frappe.get_all(
			"Item",
			filters={"delivered_by_supplier": 0, "is_sales_item": 1, "has_variants": 0},
			pluck="name",
			limit=1,
		)[0]
		mixed_order = frappe.copy_doc(self.sales_order)
		mixed_order.payment_schedule = []
		mixed_order.append(
			"items", {"item_code": store_item, "qty": 1, "rate": 649, "delivery_date": today()}
		)
		mixed_order.insert()
		mixed_order.submit()
		qikink_amount = sum(row.amount for row in mixed_order.items if row.delivered_by_supplier)
		self.assertLess(qikink_amount, mixed_order.grand_total)

		orders.send_order(mixed_order.name)

		self.assertEqual(self.created[0]["total_order_value"], qikink_amount)

	def test_a_retry_adopts_the_order_qikink_already_has(self):
		# A crash after the call leaves the order "Sending"; Qikink lists it, so it is not sent again.
		self.sales_order.db_set("commera_qikink_status", orders.SENDING_STATUS)
		self.qikink_orders = [{"order_id": 1, "number": f"654367_{self.order_number}", "status": "On Hold"}]

		self.assertEqual(orders.send_order(self.sales_order.name), self.order_number)
		self.assertEqual(self.created, [])
		self.assertEqual(self.get_qikink_fields(), (self.order_number, orders.SENT_STATUS))

	def test_a_duplicate_order_reply_adopts_the_listed_order(self):
		self.create_reply = {"error": True, "message": "Duplicate order number"}
		self.qikink_orders = [{"order_id": 1, "number": f"654367_{self.order_number}", "status": "On Hold"}]

		self.assertEqual(orders.send_order(self.sales_order.name), self.order_number)
		self.assertEqual(self.get_qikink_fields(), (self.order_number, orders.SENT_STATUS))

	def test_a_refused_order_is_not_marked_sent(self):
		self.create_reply = {"error": True, "message": "Invalid SKU"}

		with self.assertRaises(frappe.ValidationError):
			orders.send_order(self.sales_order.name)
		self.assertEqual(self.get_qikink_fields(), (None, orders.SENDING_STATUS))
		self.assertIsNone(self.get_sent_at())


class TestOrderRules(IntegrationTestCase):
	def test_order_number_is_the_digits_of_the_order_name(self):
		self.assertEqual(orders.get_order_number("SAL-ORD-2026-00062"), "202600062")

	def test_order_number_over_15_digits_throws(self):
		self.assertEqual(orders.get_order_number("SO-123456789012345"), "123456789012345")
		with self.assertRaises(frappe.ValidationError):
			orders.get_order_number("SO-2026-0000000000062")
		with self.assertRaises(frappe.ValidationError):
			orders.get_order_number("SO-NEW")

	def test_order_value_adds_the_lines_tax_share_but_no_order_charges(self):
		tee = SimpleNamespace(name="tee", net_amount=800)
		order = frappe._dict(
			taxes=[
				SimpleNamespace(name="gst", charge_type="On Net Total"),
				SimpleNamespace(name="shipping", charge_type="Actual"),
			],
			item_wise_tax_details=[
				SimpleNamespace(item_row="tee", tax_row="gst", amount=96),
				SimpleNamespace(item_row="planter", tax_row="gst", amount=77.88),
				SimpleNamespace(item_row="tee", tax_row="shipping", amount=40),
			],
			precision=lambda fieldname: 2,
		)
		self.assertEqual(orders.get_order_value(order, [(tee, None)]), 896)

	def test_unpaid_cod_goes_as_cod_and_everything_else_as_prepaid(self):
		self.assertEqual(orders.get_gateway({"payment_mode": "COD", "is_paid": False}), "COD")
		self.assertEqual(orders.get_gateway({"payment_mode": "COD", "is_paid": True}), "Prepaid")
		self.assertEqual(orders.get_gateway({"payment_mode": "Stripe", "is_paid": True}), "Prepaid")
		self.assertEqual(orders.get_gateway({"payment_mode": None, "is_paid": False}), "Prepaid")

	def test_cart_refuses_a_qikink_item_without_a_sku(self):
		item_code = get_qikink_item_code()
		item_name = frappe.db.get_value("Item", item_code, "item_name")
		other_item = frappe.get_all("Item", filters={"delivered_by_supplier": 0}, pluck="name", limit=1)[0]
		cart = SimpleNamespace(
			items=[
				SimpleNamespace(item_code=item_code, item_name=item_name),
				SimpleNamespace(item_code=other_item, item_name="Not a Qikink item"),
			]
		)
		self.assertIsNone(get_unmapped_item_refusal(cart))

		frappe.db.set_value("Item", item_code, "commera_qikink_sku", "")
		refusal = get_unmapped_item_refusal(cart)
		self.assertIn(item_name, refusal)
		self.assertNotIn("Not a Qikink item", refusal)


def get_qikink_item_code() -> str:
	item_codes = frappe.get_all("Item", filters={"commera_qikink_sku": ["is", "set"]}, pluck="name")
	qikink_items = get_qikink_items(item_codes)
	if not qikink_items:
		raise frappe.DoesNotExistError("Map one item to a Qikink SKU before running these tests")
	return next(iter(qikink_items))
