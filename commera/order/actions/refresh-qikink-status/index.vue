<script>
export const plugin = {
	label: 'Refresh Qikink status',
	icon: 'refresh-cw',
	condition: 'commera_qikink.conditions.is_sent_order',
	method: 'commera_qikink.api.refresh_order_status',
}
</script>
