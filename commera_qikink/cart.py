import frappe
from frappe import _

from commera_qikink.items import get_qikink_items


def get_unmapped_item_refusal(quotation) -> str | None:
	supplier = frappe.get_cached_doc("Qikink Settings").supplier
	item_names = {row.item_code: row.item_name for row in quotation.items}
	qikink_items = get_qikink_items(list(item_names), supplier)
	unmapped = [item_code for item_code, item in qikink_items.items() if not item.commera_qikink_sku]
	if not unmapped:
		return None
	return _("{0} can't be ordered right now. Please remove it from your cart to check out.").format(
		", ".join(sorted(item_names[item_code] for item_code in unmapped))
	)
