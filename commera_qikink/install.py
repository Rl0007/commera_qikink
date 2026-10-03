from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

MODULE = "Qikink"


def add_custom_fields():
	create_custom_fields(
		{
			"Item": [
				{
					"fieldname": "commera_qikink_sku",
					"label": "Qikink SKU",
					"fieldtype": "Data",
					"insert_after": "delivered_by_supplier",
					"module": MODULE,
				},
				{
					"fieldname": "commera_qikink_plain_product",
					"label": "Qikink Plain Product",
					"fieldtype": "Check",
					"insert_after": "commera_qikink_sku",
					"depends_on": "commera_qikink_sku",
					"module": MODULE,
				},
			]
		},
		update=True,
	)
