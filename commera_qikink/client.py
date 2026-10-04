import frappe
import requests
from frappe import _
from frappe.integrations.utils import make_get_request, make_post_request
from frappe.utils.data import cint, cstr

SANDBOX_URL = "https://sandbox.qikink.com"
LIVE_URL = "https://api.qikink.com"
# Tokens live 3600 s; renewing early keeps a request from carrying one that expires on the way.
TOKEN_TTL_SECONDS = 3500
TOKEN_LOCK_SECONDS = 30
# The legacy order endpoint is the only read the sandbox serves (order/list is 404 there); 10 orders a page.
MAX_ORDER_PAGES = 10


class QikinkError(frappe.ValidationError):
	pass


class InvalidTokenError(Exception):
	pass


class Qikink:
	def __init__(self):
		settings = frappe.get_cached_doc("Qikink Settings")
		self.client_id = cstr(settings.client_id).strip()
		self.client_secret = settings.get_password("client_secret", raise_exception=False)
		if not self.client_id or not self.client_secret:
			frappe.throw(_("Set the Qikink Client ID and Client Secret in Settings > Qikink."), QikinkError)
		self.base_url = SANDBOX_URL if settings.sandbox else LIVE_URL
		self.token_key = frappe.cache.make_key(f"commera_qikink:token:{self.base_url}:{self.client_id}")

	def create_order(self, payload: dict) -> dict:
		return self.request("POST", "/api/order/create", json=payload)

	def get_order(self, order_id: str | int) -> dict:
		return self.request("GET", "/api/order", params={"id": order_id})

	def find_order(self, order_number: str) -> dict | None:
		# Neither endpoint filters by order number on the sandbox, so page through the recent orders.
		for page_no in range(1, MAX_ORDER_PAGES + 1):
			orders = self.request("GET", "/api/order", params={"page_no": page_no})
			if not orders:
				return None
			for order in orders:
				if get_order_number(order) == order_number:
					return order
		return None

	def request(self, method: str, path: str, **kwargs) -> dict:
		token = self.get_token()
		try:
			return self.send(method, path, token, **kwargs)
		except InvalidTokenError:
			self.clear_token(token)

		try:
			return self.send(method, path, self.get_token(), **kwargs)
		except InvalidTokenError as error:
			frappe.throw(_("Qikink refused the access token: {0}").format(error), QikinkError)

	def send(self, method: str, path: str, token: str, **kwargs) -> dict:
		headers = {"ClientId": self.client_id, "Accesstoken": token}
		status, body = fetch(method, self.base_url + path, headers=headers, **kwargs)
		if error := get_error(status, body):
			if status == 401 or "token" in error.lower():
				raise InvalidTokenError(error)
			frappe.throw(_("Qikink: {0}").format(error), QikinkError)
		return body

	def get_token(self) -> str:
		if token := self.read_token():
			return token
		# One token per ClientId, and minting a new one kills the old: only one process may mint.
		with frappe.cache.lock(
			f"{self.token_key}:lock", timeout=TOKEN_LOCK_SECONDS, blocking_timeout=TOKEN_LOCK_SECONDS
		):
			return self.read_token() or self.mint_token()

	def mint_token(self) -> str:
		status, body = fetch(
			"POST",
			f"{self.base_url}/api/token",
			data={"ClientId": self.client_id, "client_secret": self.client_secret},
		)
		error = get_error(status, body)
		if error or not body.get("Accesstoken"):
			frappe.throw(_("Qikink did not issue an access token: {0}").format(error or body), QikinkError)

		expires_in = cint(body.get("expires_in"))
		ttl = min(TOKEN_TTL_SECONDS, expires_in - 100) if expires_in > 100 else TOKEN_TTL_SECONDS
		frappe.cache.set(self.token_key, body["Accesstoken"], ex=ttl)
		return body["Accesstoken"]

	def read_token(self) -> str | None:
		# Raw Redis rather than get_value: the request-local copy would hide a token another worker replaced.
		token = frappe.cache.get(self.token_key)
		return token.decode() if token else None

	def clear_token(self, token: str):
		if self.read_token() == token:
			frappe.cache.delete(self.token_key)


def fetch(method: str, url: str, **kwargs) -> tuple[int, object]:
	make_request = make_post_request if method == "POST" else make_get_request
	try:
		return 200, make_request(url, **kwargs)
	except requests.HTTPError as error:
		return error.response.status_code, read_body(error.response)
	except requests.JSONDecodeError as error:
		# Seen on an order create that Qikink went on to accept, so the order may well exist.
		frappe.throw(_("Qikink sent a reply that could not be read: {0}").format(error), QikinkError)
	except requests.RequestException as error:
		frappe.throw(_("Could not reach Qikink: {0}").format(error), QikinkError)


def read_body(response: requests.Response) -> object:
	try:
		return response.json()
	except ValueError:
		return response.text


def get_error(status: int, body: object) -> str | None:
	# Qikink can answer HTTP 200 with an error body, so the body decides as much as the status.
	if isinstance(body, dict):
		error = body.get("error")
		message = body.get("message") if error is True or body.get("success") is False else error
		if error or message or cint(body.get("status_code")) >= 400 or status >= 400:
			return cstr(message or body)
		return None
	if isinstance(body, list) and status < 400:
		return None
	if status >= 400:
		return cstr(body)[:500] or f"HTTP {status}"
	return _("Unexpected response from Qikink: {0}").format(cstr(body)[:500])


def get_order_number(order: dict) -> str:
	# Qikink prefixes the number we sent with its own account number: "654367_202600062".
	return cstr(order.get("number")).split("_", 1)[-1]
