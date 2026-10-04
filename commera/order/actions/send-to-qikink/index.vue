<script>
export const plugin = {
	label: 'Send to Qikink',
	icon: 'printer',
	condition: 'commera_qikink.conditions.can_send_order',
	method: 'commera_qikink.api.send_order',
	confirm: 'Qikink will print and ship this order, and a Purchase Order to Qikink is made. Qikink cannot cancel an order once it has it.',
}
</script>
