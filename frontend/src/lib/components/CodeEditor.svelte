<script>
  import { tick } from "svelte";
  import CodeLine from "./CodeLine.svelte";
  import FunctionBlock from "./FunctionBlock.svelte";

  export let code = "";
  export let structure = [];
  export let highlights = [];
  export let currentLine = 0;
  export let isLoading = false;
  export let isReturnState = false;
  /** When true, string hover shows edit icon and background (highlight-edit mode). */
  export let stringEditMode = false;
  /** Called when user saves a string literal edit: ({ lineIndex, startCol, endCol, newValue }) => void */
  export let onStringLiteralEdit = () => {};

  let functions = [];
  let codeEditor;
  let functionStates = new Map();
  let previousLine = 0;
  let previousFunctionId = null;
  /** { lineIndex, startCol, endCol, innerValue, quoteStart, quoteEnd } when a string is being edited */
  let editingString = null;

  /** Parse a string literal (with quotes) into inner content and quote delimiters. Single/double only. */
  function parseStringLiteral(raw) {
    if (raw.length >= 2 && raw.startsWith('"') && raw.endsWith('"'))
      return { innerValue: raw.slice(1, -1), quoteStart: '"', quoteEnd: '"' };
    if (raw.length >= 2 && raw.startsWith("'") && raw.endsWith("'"))
      return { innerValue: raw.slice(1, -1), quoteStart: "'", quoteEnd: "'" };
    return { innerValue: raw, quoteStart: '"', quoteEnd: '"' };
  }

  function onStartStringEdit({ lineIndex, startCol, endCol, value }) {
    const { innerValue, quoteStart, quoteEnd } = parseStringLiteral(value);
    editingString = {
      lineIndex,
      startCol,
      endCol,
      innerValue,
      quoteStart,
      quoteEnd,
    };
  }
  function onSaveStringEdit(innerValue) {
    if (editingString) {
      const fullValue =
        editingString.quoteStart + innerValue + editingString.quoteEnd;
      onStringLiteralEdit({
        lineIndex: editingString.lineIndex,
        startCol: editingString.startCol,
        endCol: editingString.endCol,
        newValue: fullValue,
      });
      editingString = null;
    }
  }
  function onCancelStringEdit() {
    editingString = null;
  }
  $: if (code) {
    applyBackendStructure();
  }

  /** Per-line highlight segments: [{ startCol, endCol, type }]. */
  $: lineSegments = (() => {
    if (!code || !highlights?.length) return [];
    const lines = code.split("\n");
    const segsByLine = lines.map(() => []);
    highlights.forEach((h) => {
      if (h.startLine === h.endLine) {
        const i = h.startLine;
        if (i >= 0 && i < lines.length && h.startCol < h.endCol)
          segsByLine[i].push({
            startCol: h.startCol,
            endCol: h.endCol,
            type: h.type,
          });
      } else {
        for (let i = h.startLine; i <= h.endLine; i++) {
          if (i < 0 || i >= lines.length) continue;
          const startCol = i === h.startLine ? h.startCol : 0;
          const endCol = i === h.endLine ? h.endCol : (lines[i].length ?? 0);
          if (startCol >= endCol) continue;
          segsByLine[i].push({ startCol, endCol, type: h.type });
        }
      }
    });
    return segsByLine.map((segs) => mergeSegments(segs));
  })();

  function mergeSegments(segs) {
    if (!segs.length) return [];
    segs = [...segs].sort((a, b) => a.startCol - b.startCol);
    const merged = [];
    for (const seg of segs) {
      let next = [];
      for (const m of merged) {
        if (m.endCol <= seg.startCol || m.startCol >= seg.endCol) {
          next.push(m);
        } else {
          if (m.startCol < seg.startCol)
            next.push({
              startCol: m.startCol,
              endCol: seg.startCol,
              type: m.type,
            });
          if (m.endCol > seg.endCol)
            next.push({ startCol: seg.endCol, endCol: m.endCol, type: m.type });
        }
      }
      next.push(seg);
      merged.length = 0;
      merged.push(...next);
    }
    return merged.sort((a, b) => a.startCol - b.startCol);
  }

  /** Internal (_-prefixed): show only when stepped into; otherwise hide entirely. */
  function shouldRenderFunctionBlock(func) {
    if (!func.name.startsWith("_")) return true;
    const oneBasedStart = func.startLine + 1;
    const oneBasedEnd = func.endLine + 1;
    return currentLine >= oneBasedStart && currentLine <= oneBasedEnd;
  }

  $: displayItems = (() => {
    if (!code) return [];
    const lines = code.split("\n");
    const items = [];
    let i = 0;
    while (i < lines.length) {
      const func = functions.find((f) => f.startLine === i);
      if (func && !shouldRenderFunctionBlock(func)) {
        i = func.endLine + 1;
        continue;
      }
      if (func && shouldRenderFunctionBlock(func)) {
        items.push({ type: "function", func, lines });
        i = func.endLine + 1;
        continue;
      }
      items.push({ type: "line", lineNumber: i + 1, text: lines[i] });
      i++;
    }
    return items;
  })();

  $: if (codeEditor && code) {
    void currentLine;
    void isReturnState;

    if (currentLine !== previousLine && currentLine > 0) {
      const currentFunction = findFunctionByLine(currentLine);
      const currentFunctionId = currentFunction ? currentFunction.id : null;

      if (currentFunctionId && currentFunctionId !== previousFunctionId) {
        unfoldFunctionByLine(currentLine);
      }
      if (previousFunctionId && currentFunctionId !== previousFunctionId) {
        restoreOriginalState(previousFunctionId);
      }

      previousLine = currentLine;
      previousFunctionId = currentFunctionId;
      functions = functions;
    }

    if (currentLine > 0) {
      tick().then(() => scrollCurrentLineToCenter());
    }
  }

  function scrollCurrentLineToCenter() {
    if (!codeEditor) return;
    const lineEl = codeEditor.querySelector(".current-line");
    if (lineEl) lineEl.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function applyBackendStructure() {
    const lines = code.split("\n");
    const parsedFunctions = (structure || []).map((f) => {
      const functionId = `${f.startLine}_${f.name}`;
      const defaultCollapsed = f.name.startsWith("_");
      let state;
      if (functionStates.has(functionId)) {
        state = functionStates.get(functionId);
      } else {
        state = defaultCollapsed ? "collapsed" : "expanded";
        functionStates.set(functionId, state);
      }
      const isCollapsed = state === "collapsed";
      const startLine = f.startLine;
      const endLine = Math.min(f.endLine, lines.length - 1);
      return {
        id: functionId,
        name: f.name,
        type: f.type,
        startLine,
        endLine,
        code: lines.slice(startLine, endLine + 1).join("\n"),
        collapsed: isCollapsed,
      };
    });
    functions = parsedFunctions;
  }

  function toggleFunction(functionId) {
    const currentState = functionStates.get(functionId) || "collapsed";
    const newState = currentState === "collapsed" ? "expanded" : "collapsed";
    functionStates.set(functionId, newState);

    const func = functions.find((f) => f.id === functionId);
    if (func) {
      func.collapsed = newState === "collapsed";
    }
    functions = functions;
  }

  function findFunctionByLine(lineNumber) {
    return functions.find(
      (f) => lineNumber >= f.startLine + 1 && lineNumber <= f.endLine + 1,
    );
  }

  function unfoldFunctionByLine(lineNumber) {
    const func = findFunctionByLine(lineNumber);
    if (func && func.collapsed) {
      const currentState = functionStates.get(func.id) || "collapsed";
      const newState = currentState === "collapsed" ? "temporary" : "expanded";
      functionStates.set(func.id, newState);
      func.collapsed = false;
    }
  }

  function restoreOriginalState(functionId) {
    const currentState = functionStates.get(functionId);
    if (currentState === "temporary") {
      functionStates.set(functionId, "collapsed");
      const func = functions.find((f) => f.id === functionId);
      if (func) {
        func.collapsed = true;
      }
    }
  }
</script>

<div class="code-panel">
  <div
    bind:this={codeEditor}
    class="code-editor"
    class:string-edit-mode={stringEditMode}
    contenteditable="false"
    role="document"
  >
    {#each displayItems as item}
      {#if item.type === "line"}
        <CodeLine
          text={item.text}
          lineNumber={item.lineNumber}
          segments={lineSegments[item.lineNumber - 1] ?? []}
          isCurrent={item.lineNumber === currentLine}
          {isReturnState}
          {stringEditMode}
          {editingString}
          {onStartStringEdit}
          {onSaveStringEdit}
          {onCancelStringEdit}
        />
      {:else}
        <FunctionBlock
          func={item.func}
          lines={item.lines}
          {lineSegments}
          {currentLine}
          {isReturnState}
          onToggle={toggleFunction}
          {stringEditMode}
          {editingString}
          {onStartStringEdit}
          {onSaveStringEdit}
          {onCancelStringEdit}
        />
      {/if}
    {/each}
  </div>
  {#if isLoading}
    <div class="loading-overlay">
      <div class="spinner"></div>
      <div class="loading-text">Agent is working...</div>
    </div>
  {/if}
</div>

<style>
  .code-panel {
    flex: 1;
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    padding: 0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .code-editor {
    flex: 1;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: var(--font-family-mono);
    font-size: var(--font-size-md);
    line-height: var(--line-height-base);
    padding: var(--spacing-lg);
    padding-bottom: 50vh;
    overflow-y: auto;
    overflow-x: auto;
    outline: none;
    user-select: none;
    cursor: default;
  }

  :global(.line-content) {
    flex: 1;
  }

  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--overlay-light);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: var(--z-loading);
    backdrop-filter: blur(1px);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--bg-quaternary);
    border-top: 4px solid var(--accent-blue);
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

  .loading-text {
    margin-top: var(--spacing-2xl);
    color: var(--text-muted);
    font-family: var(--font-family-mono);
    font-size: var(--font-size-md);
  }
</style>
