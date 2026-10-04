<script>
export const plugin = {
	label: 'Mark cancelled on Qikink',
	icon: 'list-checks',
	condition: 'commera_qikink.conditions.can_mark_cancelled_on_qikink',
	method: 'commera_qikink.api.mark_cancelled_on_qikink',
	confirm: 'Do this only after you cancel the order on the Qikink dashboard. The Purchase Order to Qikink is cancelled, and then you can cancel this order.',
}
</script>
