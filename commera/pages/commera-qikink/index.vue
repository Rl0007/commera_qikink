<script>
export const extension = { label: 'Qikink', icon: 'sparkles' }
</script>

<script setup>
import { computed } from 'vue'
import { EmptyState, useMethodRead, usePage } from '@commera/admin'

const summaryRequest = useMethodRead('commera_qikink.api.get_summary')
const ordersToday = computed(() => summaryRequest.data?.orders_today ?? 0)

usePage().setActions([
  {
    label: 'Refresh',
    icon: 'refresh-cw',
    loading: () => summaryRequest.loading,
    onClick: () => summaryRequest.reload(),
  },
])
</script>

<template>
  <template v-if="summaryRequest.data">
    <EmptyState
      v-if="!ordersToday"
      icon="lucide-sparkles"
      title="No store orders today"
      description="This page reads commera_qikink.api.get_summary. Build it in commera/pages/commera-qikink/index.vue, then run bench build --app commera_qikink."
    />
    <div v-else>
      <p class="text-sm text-ink-gray-5">Store orders today</p>
      <p class="mt-1 text-2xl-semibold text-ink-gray-9 tabular-nums">{{ ordersToday }}</p>
    </div>
  </template>
</template>
