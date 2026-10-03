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
			],
			"Sales Order": [
				{
					"fieldname": "commera_qikink_order_number",
					"label": "Qikink Order Number",
					"fieldtype": "Data",
					"insert_after": "po_date",
					"read_only": 1,
					"no_copy": 1,
					"module": MODULE,
				},
				{
					"fieldname": "commera_qikink_status",
					"label": "Qikink Status",
					"fieldtype": "Data",
					"insert_after": "commera_qikink_order_number",
					"read_only": 1,
					"no_copy": 1,
					"module": MODULE,
				},
				{
					"fieldname": "commera_qikink_sent_at",
					"label": "Sent to Qikink At",
					"fieldtype": "Datetime",
					"insert_after": "commera_qikink_status",
					"read_only": 1,
					"no_copy": 1,
					"module": MODULE,
				},
			],
		},
		update=True,
	)
