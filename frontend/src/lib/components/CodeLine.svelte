<script>
  import StringEditIcon from "$lib/components/icons/StringEditIcon.svelte";
  import StringEditPopover from "./StringEditPopover.svelte";

  export let text = "";
  export let lineNumber = 0;
  /** Optional: [{ startCol, endCol, type }] for syntax highlight spans. */
  export let segments = [];
  export let isCurrent = false;
  export let isReturnState = false;
  export let stringEditMode = false;
  /** Set when a string on this line is being edited: { lineIndex, startCol, endCol, value } */
  export let editingString = null;
  export let onStartStringEdit = () => {};
  export let onSaveStringEdit = () => {};
  export let onCancelStringEdit = () => {};

  $: parts = (() => {
    if (!segments.length) return [{ start: 0, end: text.length, type: null }];
    const len = text.length;
    let prev = 0;
    const out = [];
    for (const seg of segments) {
      const start = Math.max(0, Math.min(seg.startCol, len));
      const end = Math.max(start, Math.min(seg.endCol, len));
      if (start > prev) out.push({ start: prev, end: start, type: null });
      if (end > start) out.push({ start, end, type: seg.type });
      prev = end;
    }
    if (prev < len) out.push({ start: prev, end: len, type: null });
    return out;
  })();
</script>

<div
  class="code-line"
  class:current-line={isCurrent}
  class:return-line={isCurrent && isReturnState}
  data-line={lineNumber}
>
  <div class="line-content">
    {#each parts as part}
      {#if part.type}
        <span class="hl-part-wrap" role="presentation">
          {#if part.type === "string" && editingString && lineNumber - 1 === editingString.lineIndex && part.start === editingString.startCol && part.end === editingString.endCol}
            {#key editingString.lineIndex + editingString.startCol}
              <StringEditPopover
                value={editingString.innerValue}
                onSave={onSaveStringEdit}
                onCancel={onCancelStringEdit}
              />
            {/key}
          {/if}<span
            class="hl hl-{part.type.replace(/\./g, '-')}"
            role="presentation">{text.slice(part.start, part.end)}</span
          >{#if part.type === "string" && stringEditMode}
            <span
              class="string-edit-icon-wrap"
              role="button"
              tabindex="0"
              on:click|stopPropagation={() =>
                onStartStringEdit({
                  lineIndex: lineNumber - 1,
                  startCol: part.start,
                  endCol: part.end,
                  value: text.slice(part.start, part.end),
                })}
              on:keydown={(e) =>
                e.key === "Enter" &&
                onStartStringEdit({
                  lineIndex: lineNumber - 1,
                  startCol: part.start,
                  endCol: part.end,
                  value: text.slice(part.start, part.end),
                })}
            >
              <StringEditIcon />
            </span>{/if}
        </span>
      {:else}
        {text.slice(part.start, part.end)}
      {/if}
    {/each}
  </div>
</div>

<style>
  .code-line {
    display: flex;
    align-items: flex-start;
    padding: 2px var(--spacing-sm);
    margin: 1px 0;
    border-radius: var(--radius-sm);
    border-left: 3px solid transparent;
    white-space: pre-wrap;
    cursor: default;
    transition:
      background-color var(--transition-base),
      transform var(--transition-base),
      opacity var(--transition-base);
  }

  .code-line:hover {
    background-color: var(--hover-overlay);
  }

  .code-line.current-line {
    background-color: var(--debug-current-bg);
    border-left: 3px solid var(--accent-green-light);
    animation: slideDownIn 0.3s ease-out;
    color: var(--text-primary);
  }

  .code-line.current-line.return-line {
    background-color: var(--debug-return-bg);
    border-left: 3px solid var(--accent-yellow);
    color: var(--text-primary);
  }

  .line-content {
    outline: none;
    border: none;
    background: transparent;
    color: inherit;
    font-family: inherit;
    font-size: inherit;
    line-height: inherit;
    width: 100%;
    min-height: 1.2em;
    user-select: none;
    cursor: inherit;
    pointer-events: none;
  }

  @keyframes slideDownIn {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
