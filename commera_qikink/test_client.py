from unittest.mock import patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from commera_qikink.client import Qikink


class TestQikinkToken(IntegrationTestCase):
	def setUp(self):
		self.client = Qikink()
		# A key of its own, so the test never replaces the token the site is really using.
		self.client.token_key = frappe.cache.make_key("commera_qikink:test-token")
		self.addCleanup(frappe.cache.delete, self.client.token_key)
		self.tokens_seen = []
		self.minted = 0
		self.next_token = "fresh-token"
		patchers = (
			patch("commera_qikink.client.make_get_request", side_effect=self.fake_get),
			patch("commera_qikink.client.make_post_request", side_effect=self.fake_mint),
		)
		for patcher in patchers:
			patcher.start()
			self.addCleanup(patcher.stop)

	def fake_get(self, url, headers=None, params=None):
		self.tokens_seen.append(headers["Accesstoken"])
		if headers["Accesstoken"] != "fresh-token":
			response = requests.Response()
			response.status_code = 401
			response._content = b'{"error": "Invalid access token"}'
			raise requests.HTTPError(response=response)
		return [{"order_id": 1, "number": "654367_1"}]

	def fake_mint(self, url, headers=None, json=None, data=None):
		self.minted += 1
		return {"Accesstoken": self.next_token, "expires_in": 3600}

	def test_a_cached_token_is_reused(self):
		frappe.cache.set(self.client.token_key, "fresh-token")
		self.client.get_order(1)
		self.client.get_order(1)
		self.assertEqual(self.minted, 0)

	def test_a_refused_token_is_cleared_and_the_call_retried_once(self):
		frappe.cache.set(self.client.token_key, "stale-token")

		self.assertEqual(self.client.get_order(1), [{"order_id": 1, "number": "654367_1"}])
		self.assertEqual(self.tokens_seen, ["stale-token", "fresh-token"])
		self.assertEqual(self.minted, 1)
		self.assertEqual(self.client.read_token(), "fresh-token")

	def test_a_second_refusal_throws_instead_of_looping(self):
		frappe.cache.set(self.client.token_key, "stale-token")
		self.next_token = "also-stale"
		with self.assertRaises(frappe.ValidationError):
			self.client.get_order(1)
		self.assertEqual(self.tokens_seen, ["stale-token", "also-stale"])
