<script>
export const extension = { label: "Dashboard", icon: "chart-column", order: 0 };
</script>

<script setup>
import { computed, ref } from "vue";
import { Button, Dropdown, Skeleton, dayjs } from "frappe-ui";
import { BarChart, DonutChart } from "frappe-ui/charts";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from "frappe-ui/list";
import {
	EmptyState,
	ListSkeleton,
	money,
	StatusBadge,
	useExtension,
	useMethodAction,
	useMethodRead,
	usePage,
} from "@commera/admin";

const PERIODS = ["Last 7 days", "Last 30 days", "Last 12 months", "All time"];
const ROW_HEIGHT = 60;

const { navigate, toast } = useExtension();
const period = ref("Last 30 days");

const dashboardRequest = useMethodRead("commera_qikink.api.get_order_dashboard", {
	params: () => ({ period: period.value }),
	refetch: true,
});
const syncRequest = useMethodAction("commera_qikink.api.sync_open_orders");

async function syncNow() {
	await syncRequest.submit();
	if (syncRequest.error) return;
	toast.success(syncRequest.data);
	dashboardRequest.reload();
}

const pageHeader = usePage();
pageHeader.setTitle("Qikink");
pageHeader.setActions([
	{
		label: "Sync now",
		icon: "refresh-cw",
		loading: () => syncRequest.loading,
		onClick: syncNow,
	},
]);

const firstLoad = computed(() => dashboardRequest.loading && !dashboardRequest.data);
const totals = computed(() => dashboardRequest.data?.stats ?? {});
const buckets = computed(() => dashboardRequest.data?.buckets ?? []);
const byStatus = computed(() => dashboardRequest.data?.by_status ?? []);
const needsAttention = computed(() => dashboardRequest.data?.needs_attention ?? []);
const needsAttentionTotal = computed(() => dashboardRequest.data?.needs_attention_total ?? 0);
const recentOrders = computed(() => dashboardRequest.data?.recent ?? []);

function share(count) {
	return totals.value.sent ? `${Math.round((count / totals.value.sent) * 100)}% of sent` : null;
}

const stats = computed(() => [
	{
		label: "Orders sent",
		value: (totals.value.sent ?? 0).toLocaleString("en-IN"),
		note: `${money(totals.value.value ?? 0)} in orders`,
	},
	{
		label: "Delivered",
		value: (totals.value.delivered ?? 0).toLocaleString("en-IN"),
		note: share(totals.value.delivered ?? 0),
	},
	{
		label: "In progress",
		value: (totals.value.in_progress ?? 0).toLocaleString("en-IN"),
		note: "Printing or shipping",
	},
	{
		label: "Problems",
		value: (totals.value.problems ?? 0).toLocaleString("en-IN"),
		note: "See Needs attention",
	},
]);

const hasSentOrders = computed(() => buckets.value.some((bucket) => bucket.count > 0));

const noOrdersState = {
	icon: "lucide-printer",
	title: "No orders sent in this period",
	description: "Try a wider date range.",
};
</script>

<template>
	<div class="mx-auto max-w-4xl">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h1 class="text-2xl text-ink-gray-9">Orders on Qikink</h1>
				<p class="mt-1 text-p-base text-ink-gray-6">
					What Qikink is printing and shipping for the store. {{ period }}.
				</p>
			</div>
			<Dropdown
				:options="PERIODS.map((label) => ({ label, onClick: () => (period = label) }))"
			>
				<Button :label="period" icon-right="lucide-chevron-down" />
			</Dropdown>
		</div>

		<div
			class="mt-5 grid grid-cols-2 rounded-5 border border-outline-gray-1 sm:grid-cols-4 sm:divide-x sm:divide-outline-gray-2"
		>
			<div v-for="stat in stats" :key="stat.label" class="px-4 py-3.5">
				<Skeleton v-if="firstLoad" class="h-20 w-full rounded-4" />

				<template v-else>
					<p class="text-sm text-ink-gray-5">{{ stat.label }}</p>
					<p class="mt-1 text-2xl text-ink-gray-9 tabular-nums">{{ stat.value }}</p>
					<p v-if="stat.note" class="mt-1 truncate text-sm text-ink-gray-5">
						{{ stat.note }}
					</p>
					<p v-else class="mt-1 text-sm text-ink-gray-4">&nbsp;</p>
				</template>
			</div>
		</div>

		<Skeleton v-if="firstLoad" class="mt-6 h-[21.75rem] w-full rounded-5" />

		<section v-else class="mt-6 rounded-5 border border-outline-gray-1 p-4">
			<h2 class="text-lg-semibold text-ink-gray-8">Orders sent</h2>
			<EmptyState v-if="!hasSentOrders" compact v-bind="noOrdersState" />
			<div v-else class="h-72">
				<BarChart
					:data="buckets"
					x="label"
					:y="['count']"
					:series-config="{ count: { label: 'Orders' } }"
					:x-axis="{ echartOptions: { axisLabel: { rotate: 0 } } }"
					:y-axis="{ echartOptions: { minInterval: 1 } }"
				/>
			</div>
		</section>

		<div class="mt-6 grid gap-6 lg:grid-cols-2">
			<Skeleton v-if="firstLoad" class="h-[19.75rem] w-full rounded-5" />

			<section v-else class="rounded-5 border border-outline-gray-1 p-4">
				<h2 class="text-lg-semibold text-ink-gray-8">By status</h2>
				<EmptyState v-if="!byStatus.length" compact v-bind="noOrdersState" />
				<div v-else class="h-64">
					<DonutChart
						:data="byStatus"
						category="status"
						value="count"
						center-label="Orders"
					/>
				</div>
			</section>

			<Skeleton v-if="firstLoad" class="h-[19.75rem] w-full rounded-5" />

			<section v-else class="rounded-5 border border-outline-gray-1">
				<div class="flex items-center justify-between gap-3 px-4 py-3">
					<h2 class="text-lg-semibold text-ink-gray-8">Needs attention</h2>
					<span v-if="needsAttentionTotal" class="text-sm text-ink-gray-5 tabular-nums">
						{{
							needsAttention.length < needsAttentionTotal
								? `${needsAttention.length} of `
								: ""
						}}{{ needsAttentionTotal }}
					</span>
				</div>
				<div
					v-if="needsAttention.length"
					class="divide-y divide-outline-gray-1 border-t border-outline-gray-1"
				>
					<button
						v-for="order in needsAttention"
						:key="order.name"
						type="button"
						class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-1"
						@click="navigate(`/orders/${order.name}`)"
					>
						<div class="min-w-0 flex-1">
							<p class="truncate text-base text-ink-gray-8">
								{{ order.customer_name }}
							</p>
							<p class="mt-1 truncate text-sm text-ink-gray-5 tabular-nums">
								{{ order.name }}
							</p>
						</div>
						<span
							class="shrink-0 text-sm"
							:class="
								order.kind === 'problem' ? 'text-ink-red-6' : 'text-ink-gray-7'
							"
						>
							{{ order.reason }}
						</span>
					</button>
				</div>
				<div
					v-else
					class="grid min-h-48 place-items-center border-t border-outline-gray-1"
				>
					<EmptyState
						compact
						icon="lucide-circle-check"
						title="Nothing needs you"
						description="Every Qikink order is sent and on its way."
					/>
				</div>
			</section>
		</div>

		<section class="mt-6 rounded-5 border border-outline-gray-1">
			<div class="flex items-center justify-between px-4 py-3">
				<h2 class="text-lg-semibold text-ink-gray-8">Recent orders</h2>
				<Button
					variant="ghost"
					label="View all"
					icon-right="lucide-arrow-right"
					@click="navigate('orders')"
				/>
			</div>
			<div class="overflow-x-auto px-2 pb-2">
				<List
					class="max-sm:[--list-columns:minmax(0,1fr)_auto]"
					:row-height="ROW_HEIGHT"
					:columns="['1fr', '9rem', '9rem', '6rem']"
				>
					<ListHeader>
						<ListHeaderCell>Order</ListHeaderCell>
						<ListHeaderCell>Qikink status</ListHeaderCell>
						<ListHeaderCell class="max-sm:hidden">Shipment</ListHeaderCell>
						<ListHeaderCell class="max-sm:hidden">Sent</ListHeaderCell>
					</ListHeader>

					<ListSkeleton v-if="firstLoad" :columns="4" :rows="4" />

					<ListRows v-else :items="recentOrders" row-key="name" v-slot="{ item }">
						<ListRow :value="item.name" @click="navigate(`/orders/${item.name}`)">
							<ListCell>
								<div class="min-w-0">
									<p class="truncate text-base text-ink-gray-8">
										{{ item.customer_name }}
									</p>
									<p class="truncate text-sm text-ink-gray-5 tabular-nums">
										{{ item.name }}
									</p>
								</div>
							</ListCell>
							<ListCell>
								<StatusBadge
									:status="(item.status || '').toLowerCase()"
									:label="item.status"
								/>
							</ListCell>
							<ListCell class="max-sm:hidden">
								<span class="truncate text-base text-ink-gray-7">{{
									item.shipment_status || "Not shipped"
								}}</span>
							</ListCell>
							<ListCell class="max-sm:hidden">
								<span class="text-base text-ink-gray-5">{{
									dayjs(item.sent_on).format("D MMM")
								}}</span>
							</ListCell>
						</ListRow>
					</ListRows>
				</List>
			</div>

			<div
				v-if="!firstLoad && !recentOrders.length"
				class="grid min-h-48 place-items-center"
			>
				<EmptyState
					compact
					icon="lucide-printer"
					title="No orders sent to Qikink yet"
					description="Paid store orders go to Qikink on their own."
				/>
			</div>
		</section>
	</div>
</template>
