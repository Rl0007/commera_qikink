<script>
export const extension = { label: 'Qikink' }
</script>

<script setup>
import { computed } from 'vue'
import { Skeleton } from 'frappe-ui'
import { useExtension, useMethodRead } from '@commera/admin'
import { modeLabel, variantLabel } from '../../../shared/skus'

const { record } = useExtension()

const skusRequest = useMethodRead('commera_qikink.api.get_product_skus', {
	params: () => ({ item: record.value.name }),
})

const rows = computed(() => skusRequest.data ?? [])
const mappedCount = computed(() => rows.value.filter((row) => row.sku).length)
</script>

<template>
	<Skeleton v-if="skusRequest.loading && !skusRequest.data" class="h-16 w-full rounded-4" />
	<template v-else>
		<p class="text-sm text-ink-gray-5 tabular-nums">{{ mappedCount }} of {{ rows.length }} mapped to a Qikink SKU</p>
		<div class="mt-2 divide-y divide-outline-gray-1">
			<div v-for="row in rows" :key="row.item_code" class="flex items-center justify-between gap-3 py-2 last:pb-0">
				<p class="min-w-0 truncate text-base text-ink-gray-8">{{ variantLabel(row) }}</p>
				<div v-if="row.sku" class="min-w-0 text-right">
					<p class="truncate text-base text-ink-gray-8">{{ row.sku }}</p>
					<p class="text-sm text-ink-gray-5">{{ modeLabel(row) }}</p>
				</div>
				<p v-else class="text-base text-ink-gray-4">Not mapped</p>
			</div>
		</div>
	</template>
</template>
