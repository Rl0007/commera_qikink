import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils.data import add_days, add_to_date, flt, getdate, now_datetime

from commera_qikink import order_dashboard
from commera_qikink.orders import get_order_number
from commera_qikink.test_order_status import make_order

STAGES = ("sent", "delivered", "in_progress", "problems")


class TestOrderDashboard(IntegrationTestCase):
	def test_counts_sent_orders_in_the_period_by_stage(self):
		before = order_dashboard.get_dashboard("Last 30 days")["stats"]
		orders = [
			make_sent_order("Delivered", days_ago=0),
			make_sent_order("In-Transit", days_ago=0),
			make_sent_order("Returned", days_ago=3),
		]
		make_sent_order("Delivered", days_ago=40)

		after = order_dashboard.get_dashboard("Last 30 days")["stats"]
		self.assertEqual(
			{stage: after[stage] - before[stage] for stage in STAGES},
			{"sent": 3, "delivered": 1, "in_progress": 1, "problems": 1},
		)
		self.assertAlmostEqual(
			after["value"] - before["value"], sum(flt(order.base_grand_total) for order in orders), places=2
		)

	def test_buckets_orders_by_day_and_by_month(self):
		before_days = get_bucket_counts("Last 30 days")
		before_months = get_bucket_counts("Last 12 months")
		make_sent_order("Sent", days_ago=0)
		make_sent_order("Sent", days_ago=0)
		make_sent_order("Sent", days_ago=40)

		after_days = get_bucket_counts("Last 30 days")
		after_months = get_bucket_counts("Last 12 months")
		today = getdate()
		self.assertEqual(len(after_days), 30)
		self.assertEqual(list(after_days)[-1], today.strftime("%Y-%m-%d"))
		self.assertEqual(get_changes(before_days, after_days), {today.strftime("%Y-%m-%d"): 2})

		self.assertEqual(len(after_months), 12)
		self.assertEqual(
			get_changes(before_months, after_months),
			{today.strftime("%Y-%m"): 2, add_days(today, -40).strftime("%Y-%m"): 1},
		)

	def test_lists_unsent_and_problem_orders_as_needing_attention(self):
		unsent = make_order()
		returned = make_sent_order("Returned", days_ago=1)
		delivered = make_sent_order("Delivered", days_ago=1)
		from_date = add_days(getdate(), -29)

		unsent_reasons = {row["name"]: row["reason"] for row in order_dashboard.get_unsent_orders()}
		problem_reasons = {
			row["name"]: row["reason"] for row in order_dashboard.get_problem_orders(from_date)
		}
		self.assertEqual(unsent_reasons.get(unsent.name), "Not sent to Qikink")
		self.assertEqual(problem_reasons.get(returned.name), "Returned")
		self.assertNotIn(returned.name, unsent_reasons)
		self.assertNotIn(delivered.name, problem_reasons)

		unsent.db_set("commera_qikink_status", "Sending")
		unsent_reasons = {row["name"]: row["reason"] for row in order_dashboard.get_unsent_orders()}
		self.assertEqual(unsent_reasons.get(unsent.name), "Sending did not finish")

	def test_refuses_an_unknown_period(self):
		self.assertRaises(frappe.ValidationError, order_dashboard.get_dashboard, "Last 3 years")


def make_sent_order(status: str, days_ago: int):
	sales_order = make_order()
	sales_order.db_set(
		{
			"commera_qikink_order_number": get_order_number(sales_order.name),
			"commera_qikink_status": status,
			"commera_qikink_sent_at": add_to_date(now_datetime(), days=-days_ago),
		}
	)
	return sales_order


def get_bucket_counts(period: str) -> dict:
	return {bucket["key"]: bucket["count"] for bucket in order_dashboard.get_dashboard(period)["buckets"]}


def get_changes(before: dict, after: dict) -> dict:
	return {key: count - before[key] for key, count in after.items() if count != before[key]}
