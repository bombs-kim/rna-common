<script>
	import { marked } from "marked";
	import DOMPurify from "dompurify";

	export let conversationHistory = [];
	export let onNewRequest = null;

	let newRequest = "";
	let historyDisplay;
	let prevHistoryLength = 0;

	function renderMarkdown(text) {
		if (!text) return "";
		const raw = marked(text, { async: false });
		return DOMPurify.sanitize(typeof raw === "string" ? raw : "");
	}

	function handleSubmit() {
		if (newRequest.trim() && onNewRequest) {
			onNewRequest(newRequest.trim());
			newRequest = "";
		}
	}

	function scrollToBottom() {
		try {
			if (historyDisplay) {
				historyDisplay.scrollTop = historyDisplay.scrollHeight - historyDisplay.clientHeight;
			}
		} catch (_) {}
	}

	// Scroll to bottom when history length increases (initial load or new turn). Use rAF so we don't tie into Svelte's tick.
	$: len = conversationHistory.length;
	$: if (historyDisplay && len >= 0 && len !== prevHistoryLength) {
		prevHistoryLength = len;
		requestAnimationFrame(() => requestAnimationFrame(scrollToBottom));
	}
</script>

<div class="history-content">
	<div class="history-display" bind:this={historyDisplay}>
		{#if conversationHistory.length === 0}
			<div class="history-placeholder">No conversation history yet</div>
		{:else}
			{#each conversationHistory as turn}
				<div class="conversation-turn">
					<div class="user-message">
						{turn.user_prompt}
					</div>
					<div class="agent-message">
						{@html renderMarkdown(turn.agent_result)}
					</div>
				</div>
			{/each}
		{/if}
	</div>
	<div class="new-request-section">
		<textarea
			bind:value={newRequest}
			placeholder="Enter a new user request..."
			class="request-input"
			rows="3"
			on:keydown={(e) => {
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					handleSubmit();
				}
			}}
		></textarea>
		<button class="submit-button" on:click={handleSubmit}>
			Enter
		</button>
	</div>
</div>

<style>
	.history-content {
		width: 100%;
		min-width: 0;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.history-display {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overflow-x: auto;
		/* Extend into parent padding so scrollbar sits flush right; keep padding so content doesn't touch scrollbar */
		margin-right: calc(-1 * var(--spacing-xl));
		padding-left: var(--spacing-md);
		padding-right: var(--spacing-xl);
		color: var(--text-muted);
		font-size: var(--font-size-base);
		line-height: 1.5;
		box-sizing: border-box;
	}

	.history-placeholder {
		color: var(--text-secondary);
		font-style: italic;
		margin-top: var(--spacing-2xl);
	}

	.conversation-turn {
		margin-bottom: var(--spacing-2xl);
		padding-bottom: var(--spacing-xl);
		border-bottom: 1px solid var(--border-color);
	}

	.user-message {
		margin-bottom: var(--spacing-lg);
		padding: var(--spacing-md);
		background-color: #fafafa;
		border: 1px solid var(--border-color);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
	}

	.agent-message {
		margin-bottom: var(--spacing-lg);
		color: var(--text-secondary);
		word-wrap: break-word;
	}

	.agent-message :global(p) { margin: 0 0 0.5em; }
	.agent-message :global(p:last-child) { margin-bottom: 0; }
	.agent-message :global(ul), .agent-message :global(ol) { margin: 0.5em 0; padding-left: 1.5em; }
	.agent-message :global(code) { font-family: var(--font-family-mono); font-size: 0.9em; background: var(--bg-tertiary); padding: 0.1em 0.3em; border-radius: 3px; }
	.agent-message :global(pre) { margin: 0.5em 0; overflow-x: auto; }
	.agent-message :global(pre code) { background: none; padding: 0; }
	.agent-message :global(a) { color: var(--accent-blue); }
	.agent-message :global(h1), .agent-message :global(h2), .agent-message :global(h3) { margin: 0.75em 0 0.25em; font-size: 1em; font-weight: 600; }

	.new-request-section {
		margin-top: var(--spacing-xl);
		min-width: 0;
	}

	.request-input {
		box-sizing: border-box;
		width: 100%;
		max-width: 100%;
		background-color: var(--bg-primary);
		color: var(--text-muted);
		border: 1px solid var(--border-color);
		border-radius: var(--radius-sm);
		padding: var(--spacing-md);
		font-size: var(--font-size-base);
		font-family: inherit;
		resize: vertical;
		margin-bottom: var(--spacing-lg);
		transition: border-color var(--transition-base);
	}

	.request-input:focus {
		outline: none;
		border-color: var(--accent-blue);
	}

	.submit-button {
		width: 100%;
		background-color: var(--accent-blue);
		color: var(--text-white);
		border: none;
		border-radius: var(--radius-sm);
		padding: var(--spacing-md);
		font-size: var(--font-size-base);
		cursor: pointer;
		transition: background-color var(--transition-base);
	}

	.submit-button:hover {
		background-color: var(--accent-blue-hover);
	}

	.submit-button:active {
		background-color: var(--accent-blue-dark);
	}
</style>
