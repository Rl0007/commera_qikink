<script>
export const plugin = { label: 'Qikink orders', icon: 'printer', order: 1 }
</script>

<script setup>
import { computed, ref } from 'vue'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import {
	EmptyState,
	ListPagination,
	ListSkeleton,
	shortDate,
	usePlugin,
	useMethodAction,
	useMethodRead,
	usePage,
} from '@commera/admin'

const ROW_HEIGHT = 60

const { navigate, toast } = usePlugin()
const page = ref(1)
const pageSize = ref(20)

const ordersRequest = useMethodRead('commera_qikink.api.get_sent_orders', {
	params: () => ({ start: (page.value - 1) * pageSize.value, page_length: pageSize.value }),
	refetch: true,
})
const syncRequest = useMethodAction('commera_qikink.api.sync_open_orders')

async function syncNow() {
	await syncRequest.submit()
	if (syncRequest.error) return
	toast.success(syncRequest.data)
	ordersRequest.reload()
}

const pageHeader = usePage()
pageHeader.setTitle('Qikink orders')
pageHeader.setActions([
	{ label: 'Sync now', icon: 'refresh-cw', loading: () => syncRequest.loading, onClick: syncNow },
])

const rows = computed(() => ordersRequest.data?.rows ?? [])
const total = computed(() => ordersRequest.data?.total ?? 0)
const skeletonColumns = window.matchMedia('(max-width: 639.98px)').matches ? 2 : 6
</script>

<template>
	<div class="overflow-x-auto">
		<List
			class="max-sm:[--list-columns:minmax(0,1fr)_auto] sm:min-w-[54rem]"
			:row-height="ROW_HEIGHT"
			:columns="['1fr', '8rem', '8rem', '11rem', '8rem', '6rem']"
		>
			<ListHeader>
				<ListHeaderCell>Order</ListHeaderCell>
				<ListHeaderCell class="max-sm:hidden">Qikink no.</ListHeaderCell>
				<ListHeaderCell>Qikink status</ListHeaderCell>
				<ListHeaderCell class="max-sm:hidden">Purchase order</ListHeaderCell>
				<ListHeaderCell class="max-sm:hidden">Shipment</ListHeaderCell>
				<ListHeaderCell class="max-sm:hidden">Sent</ListHeaderCell>
			</ListHeader>

			<ListSkeleton v-if="ordersRequest.loading && !rows.length" :columns="skeletonColumns" />

			<ListRows v-else :items="rows" row-key="name" v-slot="{ item }">
				<ListRow :value="item.name" @click="navigate(`/orders/${item.name}`)">
					<ListCell>
						<div class="min-w-0">
							<p class="truncate text-base text-ink-gray-8">{{ item.customer_name }}</p>
							<p class="truncate text-sm text-ink-gray-5 tabular-nums">{{ item.name }}</p>
						</div>
					</ListCell>
					<ListCell class="max-sm:hidden">
						<span class="truncate text-base text-ink-gray-7 tabular-nums">{{ item.order_number }}</span>
					</ListCell>
					<ListCell>
						<span class="truncate text-base text-ink-gray-8">{{ item.status }}</span>
					</ListCell>
					<ListCell class="max-sm:hidden">
						<span class="truncate text-base text-ink-gray-7 tabular-nums">{{ item.purchase_order || '—' }}</span>
					</ListCell>
					<ListCell class="max-sm:hidden">
						<span class="truncate text-base text-ink-gray-7">{{ item.shipment_status || 'Not shipped' }}</span>
					</ListCell>
					<ListCell class="max-sm:hidden">
						<span class="text-base text-ink-gray-5">{{ shortDate(item.sent_on) }}</span>
					</ListCell>
				</ListRow>
			</ListRows>
		</List>
	</div>

	<ListPagination v-if="total" v-model:page="page" v-model:page-size="pageSize" :total="total" />

	<EmptyState
		v-if="!ordersRequest.loading && !rows.length"
		icon="lucide-printer"
		title="No orders sent to Qikink yet"
		description="Paid store orders go to Qikink on their own. Send a cash on delivery order from its More actions menu."
	/>
</template>
