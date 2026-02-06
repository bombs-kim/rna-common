<script>
  import wsManager from "$lib/utils/websocket-manager.js";
  import ExecutionStepIcons from "$lib/components/icons/ExecutionStepIcons.svelte";

  export let explanation = "";
  export let isExplanationLoading = false;
  export let variables = {};
  export let output = [];
  export let systemMessage = "";
  export let canStepInto = false;
  export let canStepOut = false;
  export let isFinished = false;

  function stepOver() {
    wsManager.stepOver();
  }

  function stepInto() {
    wsManager.stepInto();
  }

  function stepOut() {
    wsManager.stepOut();
  }

  function restart() {
    wsManager.restart();
  }
</script>

<ExecutionStepIcons />

<div class="execution-content">
  <div class="button-group">
    <button class="button step-button" disabled={isFinished} on:click={stepOver} title="Step over (next line)">
      <svg class="step-icon" aria-hidden="true"><use href="#icon-step-next"/></svg>
      Next
    </button>
    <button class="button step-button" disabled={isFinished || !canStepInto} on:click={stepInto} title="Step into">
      <svg class="step-icon" aria-hidden="true"><use href="#icon-step-into"/></svg>
      Into
    </button>
    <button class="button step-button" disabled={isFinished || !canStepOut} on:click={stepOut} title="Step out">
      <svg class="step-icon" aria-hidden="true"><use href="#icon-step-out"/></svg>
      Out
    </button>
    <button class="button step-button" on:click={restart} title="Restart">
      <svg class="step-icon" aria-hidden="true"><use href="#icon-step-restart"/></svg>
      Restart
    </button>
  </div>

  <div class="output-panel">
    <h4>Output</h4>
    <div class="output-display">
      {#if output.length === 0}
        <span class="placeholder">No output yet</span>
      {:else}
        {#each output as line}
          <div>{line}</div>
        {/each}
      {/if}
    </div>
  </div>

  <div class="explanation-panel">
    <h4>Explanation</h4>
    <div class="explanation-display">
      {#if isExplanationLoading}
        <div class="loading-container">
          <div class="spinner"></div>
          <span class="placeholder">Loading explanation...</span>
        </div>
      {:else if explanation}
        {explanation}
      {:else}
        <span class="placeholder">No explanation available</span>
      {/if}
    </div>
  </div>

  <div class="system-message-panel">
    <h4>System Message</h4>
    <div class="system-message-display">
      {#if systemMessage}
        {systemMessage}
      {:else}
        <span class="placeholder">No system message</span>
      {/if}
    </div>
  </div>

  <div class="variables-panel">
    <h4>Variables</h4>
    <div class="variables-display">
      {#if Object.keys(variables).length === 0}
        <span class="placeholder">No variables</span>
      {:else}
        {#each Object.entries(variables) as [name, value]}
          <div class="variable-item">
            <strong>{name}:</strong>
            {String(value)}
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

<style>
  .execution-content {
    width: 100%;
  }

  .button-group {
    display: flex;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-md);
  }

  .step-icon {
    width: 2.03em;
    height: 2.03em;
    vertical-align: -0.3em;
    margin-right: 0.53em;
  }

  .step-button {
    background-color: var(--accent-green);
    color: var(--text-white);
    border: 1px solid var(--accent-green-hover);
    padding: var(--spacing-md) var(--spacing-lg);
    font-size: var(--font-size-sm);
    margin: 0;
    flex: 1;
    transition: background-color var(--transition-base);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .step-button:hover:not(:disabled) {
    background-color: var(--accent-green-hover);
  }

  .step-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);
  }

  .placeholder {
    color: var(--text-secondary);
    font-style: italic;
  }

  .loading-container {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid var(--bg-quaternary);
    border-top: 2px solid var(--accent-green);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  .execution-content h4 {
    margin: var(--spacing-xs) 0;
    font-size: var(--font-size-md);
  }

  .output-panel,
  .explanation-panel,
  .system-message-panel,
  .variables-panel {
    margin-top: var(--spacing-md);
    background-color: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
  }

  .explanation-panel {
    height: 75px;
  }

  .variables-panel {
    height: 150px;
  }

  .output-panel {
    height: 200px;
  }

  .system-message-panel {
    height: 75px;
  }

  .explanation-display,
  .variables-display,
  .output-display,
  .system-message-display {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .variable-item {
    margin: var(--spacing-sm) 0;
    padding: var(--spacing-sm);
    background-color: var(--bg-tertiary);
    border-radius: var(--radius-sm);
  }
</style>
