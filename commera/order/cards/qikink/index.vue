<script>
export const extension = { label: 'Qikink' }
</script>

<script setup>
import { computed, watch } from 'vue'
import { Skeleton } from 'frappe-ui'
import { useCard, useExtension, useMethodRead } from '@commera/admin'

const { record } = useExtension()
const card = useCard()

const cardRequest = useMethodRead('commera_qikink.api.get_order_card', {
	params: () => ({ sales_order: record.value.name }),
})

const qikink = computed(() => cardRequest.data)
watch(qikink, (data) => card.setHidden(!!data && !data.has_qikink_lines), { immediate: true })
</script>

<template>
	<Skeleton v-if="cardRequest.loading && !qikink" class="h-16 w-full rounded-4" />
	<div v-else-if="qikink" class="divide-y divide-outline-gray-1">
		<div class="flex items-start justify-between gap-3 pb-2">
			<div class="min-w-0">
				<p class="text-sm text-ink-gray-5">Qikink order</p>
				<p class="truncate text-base text-ink-gray-8 tabular-nums">{{ qikink.order_number || 'Not sent yet' }}</p>
			</div>
			<div v-if="qikink.order_number" class="min-w-0 text-right">
				<p class="text-sm text-ink-gray-5">Qikink status</p>
				<p class="truncate text-base text-ink-gray-8">{{ qikink.status }}</p>
			</div>
		</div>
		<div v-if="qikink.purchase_orders.length" class="py-2">
			<p class="text-sm text-ink-gray-5">Drop-ship purchase order</p>
			<a
				v-for="purchaseOrder in qikink.purchase_orders"
				:key="purchaseOrder"
				:href="`/desk/purchase-order/${purchaseOrder}`"
				target="_blank"
				class="block truncate text-base font-medium text-ink-gray-8 hover:underline"
			>
				{{ purchaseOrder }}
			</a>
		</div>
		<div v-for="shipment in qikink.shipments" :key="shipment.name" class="flex items-start justify-between gap-3 py-2 last:pb-0">
			<div class="min-w-0">
				<p class="text-sm text-ink-gray-5">{{ shipment.carrier || 'Courier not named' }} · {{ shipment.status }}</p>
				<p class="truncate text-base text-ink-gray-8 tabular-nums">AWB {{ shipment.awb }}</p>
			</div>
			<a
				v-if="shipment.tracking_url"
				:href="shipment.tracking_url"
				target="_blank"
				rel="noopener"
				class="shrink-0 text-base font-medium text-ink-gray-8 hover:underline"
			>
				Track
			</a>
		</div>
	</div>
</template>
