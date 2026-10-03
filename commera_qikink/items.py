import frappe
from frappe.query_builder import DocType


def get_qikink_items(item_codes: list[str], supplier: str) -> dict:
	"""Keyed by item code; each row has commera_qikink_sku and commera_qikink_plain_product."""
	if not item_codes or not supplier:
		return {}
	# A Qikink item is one Qikink drop-ships: delivered by supplier, with the Qikink supplier as default.
	item = DocType("Item")
	item_default = DocType("Item Default")
	rows = (
		frappe.qb.from_(item)
		.join(item_default)
		.on((item_default.parent == item.name) & (item_default.parenttype == "Item"))
		.select(item.name, item.commera_qikink_sku, item.commera_qikink_plain_product)
		.distinct()
		.where(
			item.name.isin(item_codes)
			& (item.delivered_by_supplier == 1)
			& (item_default.default_supplier == supplier)
		)
		.run(as_dict=True)
	)
	return {row.name: row for row in rows}
