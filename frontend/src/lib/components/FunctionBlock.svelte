<script>
  import CodeLine from "./CodeLine.svelte";
  import StringEditIcon from "./StringEditIcon.svelte";
  import StringEditPopover from "./StringEditPopover.svelte";

  export let func;
  export let lines = [];
  /** Per-line segments from CodeEditor (0-based index -> segments) */
  export let lineSegments = [];
  export let currentLine = 0;
  export let isReturnState = false;
  export let onToggle = () => {};
  export let stringEditMode = false;
  /** Set when a string is being edited: { lineIndex, startCol, endCol, value } */
  export let editingString = null;
  export let onStartStringEdit = () => {};
  export let onSaveStringEdit = () => {};
  export let onCancelStringEdit = () => {};

  $: signatureText = lines[func.startLine] ?? "";
  $: signatureSegments = lineSegments[func.startLine] ?? [];
  $: signatureParts = (() => {
    if (!signatureSegments.length) return [{ start: 0, end: signatureText.length, type: null }];
    let prev = 0;
    const out = [];
    for (const seg of signatureSegments) {
      if (seg.startCol > prev) out.push({ start: prev, end: seg.startCol, type: null });
      out.push({ start: seg.startCol, end: seg.endCol, type: seg.type });
      prev = seg.endCol;
    }
    if (prev < signatureText.length) out.push({ start: prev, end: signatureText.length, type: null });
    return out;
  })();
  $: isDefining = currentLine === func.startLine + 1;
  $: displayEnd = (() => {
    let end = func.endLine;
    while (end >= func.startLine + 1 && lines[end].trim() === "") end--;
    return end;
  })();
  $: bodyLines = (() => {
    const out = [];
    for (let j = func.startLine + 1; j <= displayEnd; j++) {
      out.push({ text: lines[j], lineNumber: j + 1 });
    }
    return out;
  })();
</script>

<div class="function-block" data-function-id={func.id}>
  <div
    class="function-header"
    class:collapsed={func.collapsed}
    class:defining={isDefining}
    role="button"
    tabindex="0"
    on:click={() => onToggle(func.id)}
    on:keydown={(e) => e.key === "Enter" && onToggle(func.id)}
  >
    <span class="collapse-icon">{func.collapsed ? "▶" : "▼"}</span>
    <span class="function-signature">
      {#each signatureParts as part}
        {#if part.type}
          <span class="hl-part-wrap" role="presentation">
            {#if part.type === "string" && editingString && func.startLine === editingString.lineIndex && part.start === editingString.startCol && part.end === editingString.endCol}
              {#key editingString.lineIndex + editingString.startCol}
                <StringEditPopover
                  value={editingString.innerValue}
                  onSave={onSaveStringEdit}
                  onCancel={onCancelStringEdit}
                />
              {/key}
            {/if}
            <span
              class="hl hl-{part.type.replace(/\./g, '-')}"
              role="presentation"
            >{signatureText.slice(part.start, part.end)}</span>{#if part.type === "string" && stringEditMode}
              <span class="string-edit-icon-wrap" role="button" tabindex="0" on:click|stopPropagation={() => onStartStringEdit({ lineIndex: func.startLine, startCol: part.start, endCol: part.end, value: signatureText.slice(part.start, part.end) })} on:keydown={(e) => e.key === "Enter" && onStartStringEdit({ lineIndex: func.startLine, startCol: part.start, endCol: part.end, value: signatureText.slice(part.start, part.end) })}>
                <StringEditIcon />
              </span>
            {/if}
          </span>
        {:else}
          {signatureText.slice(part.start, part.end)}
        {/if}
      {/each}
    </span>
  </div>
  {#if !func.collapsed}<div class="function-body">
      {#each bodyLines as { text, lineNumber }}
        <CodeLine
          {text}
          {lineNumber}
          segments={lineSegments[lineNumber - 1] ?? []}
          isCurrent={lineNumber === currentLine}
          {isReturnState}
          {stringEditMode}
          editingString={editingString}
          {onStartStringEdit}
          {onSaveStringEdit}
          {onCancelStringEdit}
        />
      {/each}
    </div>{/if}
</div>

<style>
  .function-block {
    margin: 2px 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    background: transparent;
    display: flex;
    flex-direction: column;
  }

  .function-header {
    display: flex;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-lg);
    cursor: pointer;
    background-color: var(--bg-quaternary);
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    user-select: none;
    transition: background-color var(--transition-base);
  }

  .function-header:hover {
    background-color: var(--bg-hover);
  }

  .function-header.collapsed {
    border-radius: var(--radius-sm);
  }

  .function-header.defining {
    background-color: var(--bg-hover);
    border-left: 4px solid var(--accent-blue);
  }

  .collapse-icon {
    margin-right: var(--spacing-md);
    color: var(--accent-blue);
    font-weight: bold;
    transition: transform var(--transition-base);
    font-size: var(--font-size-sm);
    min-width: var(--spacing-sm);
  }

  .function-signature {
    color: var(--text-primary);
    font-family: var(--font-family-mono);
    font-size: var(--font-size-md);
    line-height: var(--line-height-base);
  }

  .function-signature :global(.hl) {
    pointer-events: auto;
  }

  .function-body {
    padding: var(--spacing-sm) var(--spacing-lg);
    background-color: var(--bg-primary);
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
    max-height: none;
    overflow: hidden;
    transition:
      max-height var(--transition-slow),
      padding var(--transition-slow);
    display: flex;
    flex-direction: column;
  }

  @keyframes collapse {
    from {
      max-height: 1000px;
      opacity: 1;
    }
    to {
      max-height: 0;
      opacity: 0;
    }
  }

  @keyframes expand {
    from {
      max-height: 0;
      opacity: 0;
    }
    to {
      max-height: 1000px;
      opacity: 1;
    }
  }
</style>
