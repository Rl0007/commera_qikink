from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from commera_qikink import order_status
from commera_qikink.client import Qikink
from commera_qikink.orders import get_order_number
from commera_qikink.purchase_orders import make_drop_ship_order


class TestOrderStatus(IntegrationTestCase):
	def setUp(self):
		self.sales_order = make_sent_order()
		# The Shipping Request needs an origin, which a partner shipment takes from the order's company address.
		self.sales_order.db_set("company_address", make_company_address(self.sales_order.company))
		self.order_number = get_order_number(self.sales_order.name)
		# Unique per test: the database rolls back once per class, and awb is unique.
		self.awb = f"QKTEST{self.order_number}"
		if not make_drop_ship_order(self.sales_order):
			self.skipTest("No buying price for the Qikink item on the settings' buying price list")
		self.qikink_pages = {}
		self.get_patch = patch("commera_qikink.client.make_get_request", side_effect=self.fake_get)
		self.post_patch = patch(
			"commera_qikink.client.make_post_request", side_effect=AssertionError("no POST")
		)
		self.token_patch = patch.object(Qikink, "get_token", return_value="test-token")
		for patcher in (self.get_patch, self.post_patch, self.token_patch):
			patcher.start()
			self.addCleanup(patcher.stop)

	def fake_get(self, url, headers=None, params=None):
		return self.qikink_pages.get(params["page_no"], [])

	def set_qikink_order(self, status, awb=None, page_no=1):
		other_order = {"order_id": 2, "number": "654367_1", "status": "On Hold", "shipping": {}}
		self.qikink_pages = {page: [other_order] for page in range(1, page_no)}
		self.qikink_pages[page_no] = [
			{
				"order_id": 1,
				"number": f"654367_{self.order_number}",
				"status": status,
				"shipping": {
					"awb": awb,
					"courier_provider_name": "Delhivery" if awb else None,
					"tracking_link": f"https://courierupdates.com/?awb={awb or ''}",
				},
			}
		]

	def get_shipments(self):
		return frappe.get_all(
			"Shipping Request",
			filters={"ref_doctype": "Sales Order", "ref_docname": self.sales_order.name},
			fields=["awb", "carrier", "status", "tracking_url", "provider"],
		)

	def get_received_qty(self):
		return frappe.get_all(
			"Purchase Order Item",
			filters={"sales_order": self.sales_order.name, "docstatus": 1},
			fields=["qty", "received_qty"],
		)

	def test_production_status_is_saved_without_a_shipment(self):
		self.set_qikink_order("To be Printed")
		self.assertEqual(order_status.refresh_order_status(self.sales_order.name), "To be Printed")
		self.assertEqual(self.get_shipments(), [])

	def test_awb_records_a_partner_shipment(self):
		self.set_qikink_order("In-Transit", awb=self.awb, page_no=2)
		order_status.refresh_order_status(self.sales_order.name)

		shipments = self.get_shipments()
		self.assertEqual(len(shipments), 1)
		self.assertEqual(shipments[0].awb, self.awb)
		self.assertEqual(shipments[0].carrier, "Delhivery")
		self.assertEqual(shipments[0].status, "In Transit")
		self.assertEqual(shipments[0].tracking_url, f"https://courierupdates.com/?awb={self.awb}")
		self.assertIsNone(shipments[0].provider)
		self.assertEqual([row.received_qty for row in self.get_received_qty()], [0])

	def test_delivered_delivers_the_drop_ship_order_once(self):
		self.set_qikink_order("Delivered", awb=self.awb)
		order_status.refresh_order_status(self.sales_order.name)
		order_status.refresh_order_status(self.sales_order.name)

		self.assertEqual(self.get_shipments()[0].status, "Delivered")
		for row in self.get_received_qty():
			self.assertEqual(row.received_qty, row.qty)
		self.assertEqual(frappe.db.get_value("Sales Order", self.sales_order.name, "per_delivered"), 100)
		self.assertNotIn(self.order_number, order_status.get_open_orders())

	def test_scheduler_logs_a_failing_order_and_keeps_its_status(self):
		self.set_qikink_order("Delivered", awb=self.awb)
		with patch.object(
			order_status, "deliver_drop_ship_order", side_effect=frappe.ValidationError("boom")
		):
			order_status.sync_open_orders()

		self.assertEqual(
			frappe.db.get_value("Sales Order", self.sales_order.name, "commera_qikink_status"), "Sent"
		)
		self.assertTrue(
			frappe.db.exists(
				"Error Log", {"reference_doctype": "Sales Order", "reference_name": self.sales_order.name}
			)
		)

	def test_unlisted_order_refuses_to_refresh(self):
		with self.assertRaises(frappe.ValidationError):
			order_status.refresh_order_status(self.sales_order.name)


def make_sent_order():
	sales_order = make_order()
	sales_order.db_set(
		{"commera_qikink_order_number": get_order_number(sales_order.name), "commera_qikink_status": "Sent"}
	)
	return sales_order


def make_order():
	"""A submitted copy of the Qikink lines of the newest order sent to Qikink, not sent itself."""
	template = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "commera_qikink_order_number": ["is", "set"]},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if not template:
		raise frappe.DoesNotExistError("Send one order to Qikink before running these tests")
	sales_order = frappe.copy_doc(frappe.get_doc("Sales Order", template[0]))
	sales_order.update(
		{
			"transaction_date": today(),
			"delivery_date": None,
			"payment_schedule": [],
			"commera_qikink_order_number": None,
			"commera_qikink_status": None,
			"commera_qikink_sent_at": None,
		}
	)
	# The newest order may be a mixed cart; the store's own lines would hold back per_delivered.
	sales_order.items = [row for row in sales_order.items if row.delivered_by_supplier]
	for row in sales_order.items:
		# Copied as they are: the quotation link would overbill it, and ordered_qty hides it from the PO mapper.
		row.prevdoc_docname = row.quotation_item = None
		row.ordered_qty = row.delivered_qty = 0
	sales_order.insert()
	sales_order.submit()
	return sales_order


def make_company_address(company: str) -> str:
	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": company,
			"address_line1": "1 Test Street",
			"city": "Bengaluru",
			"country": "India",
			"is_your_company_address": 1,
			"links": [{"link_doctype": "Company", "link_name": company}],
		}
	).insert()
	return address.name
