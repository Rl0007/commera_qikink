import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils.data import cint, cstr

MAX_SKU_LENGTH = 50
ITEM_FIELDS = [
	"name as item_code",
	"item_name",
	"commera_qikink_sku as sku",
	"commera_qikink_plain_product as plain_product",
]


def get_product_skus(item_template: str) -> list[dict]:
	return get_chain_rows(item_template) or get_variant_rows(item_template) or get_own_rows(item_template)


def save_product_skus(item_template: str, skus: list[dict]) -> list[dict]:
	current = {row.item_code for row in get_product_skus(item_template)}
	entries = [get_entry(row, current, item_template) for row in skus]
	mapped = [entry["item_code"] for entry in entries if entry["sku"]]
	supplier = get_qikink_supplier() if mapped else None

	for entry in entries:
		values = {"commera_qikink_sku": entry["sku"] or None, "commera_qikink_plain_product": entry["plain"]}
		if entry["sku"]:
			values["delivered_by_supplier"] = 1
		frappe.db.set_value("Item", entry["item_code"], values)
	if mapped:
		set_default_supplier(mapped, supplier)
	return get_product_skus(item_template)


def get_chain_rows(item_template: str) -> list[dict]:
	color_size_item = DocType("Color Size Item")
	variant = DocType("Style Attribute Variant")
	configurator = DocType("Style Attribute Configurator")
	item = DocType("Item")
	return (
		frappe.qb.from_(color_size_item)
		.join(variant)
		.on(variant.name == color_size_item.parent)
		.join(configurator)
		.on(configurator.name == variant.configurator)
		.join(item)
		.on(item.name == color_size_item.item_code)
		.select(
			color_size_item.item_code,
			item.item_name,
			variant.attribute_value.as_("colour"),
			color_size_item.size,
			item.commera_qikink_sku.as_("sku"),
			item.commera_qikink_plain_product.as_("plain_product"),
		)
		.where(
			(configurator.item_template == item_template)
			& (color_size_item.parenttype == "Style Attribute Variant")
		)
		.orderby(variant.creation)
		.orderby(color_size_item.idx)
		.run(as_dict=True)
	)


def get_variant_rows(item_template: str) -> list[dict]:
	return frappe.get_all(
		"Item",
		filters={"variant_of": item_template, "disabled": 0},
		fields=ITEM_FIELDS,
		order_by="name asc",
	)


def get_own_rows(item_template: str) -> list[dict]:
	return frappe.get_all(
		"Item",
		filters={"name": item_template},
		fields=ITEM_FIELDS,
	)


def get_entry(row: dict, current: set, item_template: str) -> dict:
	item_code = cstr(row.get("item_code"))
	if item_code not in current:
		frappe.throw(_("{0} is not an item of product {1}.").format(item_code, item_template))

	sku = cstr(row.get("sku")).strip()
	if len(sku) > MAX_SKU_LENGTH:
		frappe.throw(_("A Qikink SKU has at most {0} characters: {1}").format(MAX_SKU_LENGTH, sku))
	return {"item_code": item_code, "sku": sku, "plain": cint(row.get("plain_product")) if sku else 0}


def get_qikink_supplier() -> str:
	supplier = frappe.db.get_single_value("Qikink Settings", "supplier")
	if not supplier:
		frappe.throw(
			_(
				"Choose the Qikink supplier first, in Settings > Installed plugins > Qikink. "
				"Qikink ships these products for you, so each one is bought from that supplier."
			)
		)
	return supplier


def set_default_supplier(item_codes: list[str], supplier: str):
	company = get_store_company()
	defaults = frappe.get_all(
		"Item Default",
		filters={"parenttype": "Item", "parent": ["in", item_codes]},
		fields=["name", "parent", "company"],
	)
	row_counts = {}
	company_rows = {}
	for row in defaults:
		row_counts[row.parent] = row_counts.get(row.parent, 0) + 1
		if row.company == company:
			company_rows[row.parent] = row.name

	for item_code in item_codes:
		if item_code in company_rows:
			frappe.db.set_value("Item Default", company_rows[item_code], "default_supplier", supplier)
			continue
		frappe.get_doc(
			{
				"doctype": "Item Default",
				"parenttype": "Item",
				"parentfield": "item_defaults",
				"parent": item_code,
				"idx": row_counts.get(item_code, 0) + 1,
				"company": company,
				"default_supplier": supplier,
			}
		).db_insert()


def get_store_company() -> str:
	# Same fallback Commera uses when it makes a cart.
	return frappe.get_cached_doc("Commera Settings").get("company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
