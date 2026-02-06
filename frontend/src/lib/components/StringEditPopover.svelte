<script>
  import { onMount } from "svelte";

  /** Initial value (literal text including quotes). */
  export let value = "";
  export let onSave = (v) => {};
  export let onCancel = () => {};

  let draftValue = value;
  let inputEl;

  onMount(() => {
    draftValue = value;
    inputEl?.focus();
  });

  function handleKeydown(e) {
    if (e.key === "Escape") onCancel();
    if (e.key === "Enter") onSave(draftValue);
  }
</script>

<div class="string-edit-popover" role="dialog" aria-label="Edit string literal">
  <input
    bind:this={inputEl}
    bind:value={draftValue}
    type="text"
    class="string-edit-input"
    on:keydown={handleKeydown}
  />
  <div class="string-edit-actions">
    <button type="button" class="string-edit-btn string-edit-btn-ok" on:click={() => onSave(draftValue)} title="Save" aria-label="Save">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </button>
    <button type="button" class="string-edit-btn string-edit-btn-cancel" on:click={onCancel} title="Cancel" aria-label="Cancel">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>
  </div>
</div>

<style>
  .string-edit-popover {
    position: absolute;
    left: 0;
    bottom: 100%;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    z-index: 10;
  }
  .string-edit-input {
    min-width: 120px;
    padding: 4px 8px;
    font-family: var(--font-family-mono);
    font-size: inherit;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    background: var(--bg-primary);
    color: var(--text-primary);
  }
  .string-edit-input:focus {
    outline: none;
    border-color: var(--accent-blue);
  }
  .string-edit-actions {
    display: flex;
    gap: 4px;
  }
  .string-edit-btn {
    width: 28px;
    height: 28px;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    cursor: pointer;
    background: var(--bg-secondary);
    color: var(--text-primary);
  }
  .string-edit-btn:hover {
    background: var(--bg-tertiary);
  }
  .string-edit-btn-ok {
    color: var(--accent-green);
    border-color: var(--accent-green);
  }
  .string-edit-btn-ok:hover {
    background: var(--accent-green);
    color: var(--text-white);
  }
  .string-edit-btn-cancel {
    color: var(--accent-red);
    border-color: var(--accent-red);
  }
  .string-edit-btn-cancel:hover {
    background: var(--accent-red);
    color: var(--text-white);
  }
</style>
