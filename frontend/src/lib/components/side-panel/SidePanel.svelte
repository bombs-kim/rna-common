<script>
	/** @type {"edit" | "execution"} */
	export let mode = "edit";
	/** @type {import("svelte").Snippet} */
	export let historyPanel;
	/** @type {import("svelte").Snippet} */
	export let executionPanel;
</script>

<div class="side-panel">
	{#if mode === "execution" && executionPanel}
		{@render executionPanel()}
	{:else if historyPanel}
		{@render historyPanel()}
	{/if}
</div>

<style>
	.side-panel {
		width: var(--panel-width);
		min-width: 0;
		min-height: 0;
		display: flex;
		flex-direction: column;
		background-color: var(--bg-secondary);
		border: 1px solid var(--border-color);
		border-radius: var(--radius-md);
		padding: var(--spacing-xl);
	}
</style>
