import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce


def get_unmapped_item_refusal(quotation) -> str | None:
	supplier = frappe.get_cached_doc("Qikink Settings").supplier
	item_names = {row.item_code: row.item_name for row in quotation.items}
	if not supplier or not item_names:
		return None

	unmapped = get_unmapped_qikink_items(list(item_names), supplier)
	if not unmapped:
		return None
	return _("{0} can't be ordered right now. Please remove it from your cart to check out.").format(
		", ".join(sorted(item_names[item_code] for item_code in unmapped))
	)


def get_unmapped_qikink_items(item_codes: list[str], supplier: str) -> list[str]:
	# A Qikink item is one Qikink drop-ships: delivered by supplier, with the Qikink supplier as default.
	item = DocType("Item")
	item_default = DocType("Item Default")
	return (
		frappe.qb.from_(item)
		.join(item_default)
		.on((item_default.parent == item.name) & (item_default.parenttype == "Item"))
		.select(item.name)
		.distinct()
		.where(
			item.name.isin(item_codes)
			& (item.delivered_by_supplier == 1)
			& (item_default.default_supplier == supplier)
			& (Coalesce(item.commera_qikink_sku, "") == "")
		)
		.run(pluck=True)
	)
