<script>
export const extension = {
	label: 'Set Qikink SKUs',
	icon: 'tag',
	condition: 'commera_qikink.conditions.can_edit_item',
}
</script>

<script setup>
import { ref, watch } from 'vue'
import { FormControl } from 'frappe-ui'
import { useAction, useExtension, useMethodAction, useMethodRead } from '@commera/admin'
import { variantLabel } from '../../../shared/skus'

const { record, toast } = useExtension()
const action = useAction()
const rows = ref([])

const skusRequest = useMethodRead('commera_qikink.api.get_product_skus', {
	params: () => ({ item: record.value.name }),
})
watch(
	() => skusRequest.data,
	(data) => {
		rows.value = (data ?? []).map((row) => ({ ...row, sku: row.sku ?? '', plain_product: !!row.plain_product }))
	},
	{ immediate: true },
)

const saveRequest = useMethodAction('commera_qikink.api.save_product_skus')

action.setPrimary({ label: 'Save SKUs', loading: () => skusRequest.loading || saveRequest.loading })

action.onSubmit(async () => {
	const skus = rows.value.map((row) => ({
		item_code: row.item_code,
		sku: row.sku.trim(),
		plain_product: row.plain_product ? 1 : 0,
	}))
	await saveRequest.submit({ item: record.value.name, skus })
	if (saveRequest.error) throw saveRequest.error
	toast.success('Qikink SKUs saved')
	return { reload: true }
})
</script>

<template>
	<p class="text-base text-ink-gray-7">
		Enter the SKU from Qikink's My Products page, or tick Plain for a blank catalog product printed with no
		design. Mapped sizes are drop-shipped by your Qikink supplier.
	</p>
	<div class="mt-3 divide-y divide-outline-gray-1">
		<div v-for="row in rows" :key="row.item_code" class="flex items-center gap-3 py-2">
			<p class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ variantLabel(row) }}</p>
			<FormControl v-model="row.sku" class="w-48 shrink-0" placeholder="Not mapped" :maxlength="50" />
			<FormControl v-model="row.plain_product" type="checkbox" label="Plain" />
		</div>
	</div>
</template>
