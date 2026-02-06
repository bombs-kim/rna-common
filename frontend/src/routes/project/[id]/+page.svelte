<script>
  import { onDestroy, onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import CodeEditor from "$lib/components/CodeEditor.svelte";
  import SidePanel from "$lib/components/side-panel/SidePanel.svelte";
  import ExecutionPanel from "$lib/components/side-panel/ExecutionPanel.svelte";
  import HistoryPanel from "$lib/components/side-panel/HistoryPanel.svelte";
  import wsManager from "$lib/utils/websocket-manager.js";

  const API_URL = import.meta.env.VITE_API_URL;

  let projectId = $page.params.id;
  let mode = "edit";
  let code = "";
  let structure = [];
  let highlights = [];
  let currentLine = 0;
  let status = "Disconnected";
  let explanation = "";
  let isExplanationLoading = false;
  let variables = {};
  let output = [];
  let systemMessage = "";
  let conversationHistory = [];
  let isAgentLoading = false;
  let canStepInto = false;
  let canStepOut = false;
  let isReturnState = false;
  let isFinished = false;

  $: {
    const modeParam = $page.url.searchParams.get("mode");
    mode = modeParam === "execution" ? "execution" : "edit";
  }

  onMount(async () => {
    // Load project code
    await loadProjectCode();

    // Load conversation history
    await loadConversationHistory();

    // Connect WebSocket
    wsManager.setHandlers({
      updateStatus: (msg) => {
        status = msg;
      },
      handleExplanation: (data) => {
        explanation = data.explanation || "";
        isExplanationLoading = false; // Clear loading state
      },
      handleState: (data) => {
        console.log("[handleState] Received data:", data);
        console.log(
          "[handleState] can_step_into:",
          data.can_step_into,
          "can_step_out:",
          data.can_step_out
        );
        currentLine = data.line_number || 0;
        variables = data.local_vars || {};
        systemMessage = data.system_message || "";
        canStepInto = data.can_step_into;
        canStepOut = data.can_step_out;
        // Check if this is a return state based on system_message
        isReturnState = data.system_message === "return";
        isFinished = !!data.is_main_finished; // Use is_main_finished from state

        // If has_explanation flag is set (for step_over), prepare for explanation
        if (data.has_explanation) {
          explanation = ""; // Clear explanation while waiting for new one
          isExplanationLoading = true; // Set loading state
        }

        console.log(
          "[handleState] After assignment - isFinished:",
          isFinished,
          "canStepInto:",
          canStepInto,
          "canStepOut:",
          canStepOut,
          "isReturnState:",
          isReturnState
        );
        if (data.program_output && typeof data.program_output === "string") {
          output = data.program_output.split("\n");
        }
      },
      handleRestart: () => {
        variables = {};
        output = [];
        systemMessage = "";
        explanation = "";
        isExplanationLoading = false;
        canStepInto = false;
        canStepOut = false;
        isReturnState = false;
        isFinished = false;
      },
      handleFinished: (data) => {
        isFinished = true;
        currentLine = 0; // Clear line highlight when program finishes
        if (data.program_output && typeof data.program_output === "string") {
          output = data.program_output.split("\n");
        }
        systemMessage = data.system_message || "Program execution finished";
      },
      handleAgentResult: async (data) => {
        // Reload conversation history and code when agent result is received
        isAgentLoading = false;
        await loadConversationHistory();
        await loadProjectCode();
      },
    });
    // Always connect to project WebSocket for agent_result
    wsManager.connectProject(projectId);
    // Connect to debug WebSocket only in execution mode
    const modeParam = $page.url.searchParams.get("mode");
    const initialMode = modeParam === "execution" ? "execution" : "edit";
    if (initialMode === "execution") {
      wsManager.connectDebug();
    }
  });

  onDestroy(() => {
    wsManager.disconnect();
  });

  async function loadProjectCode() {
    if (!API_URL) {
      code = "# Error: VITE_API_URL is not set";
      structure = [];
      return;
    }
    try {
      const response = await fetch(`${API_URL}/api/projects/${projectId}/code`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      code = data.content ?? "# start by generating code";
      structure = data.functions ?? [];
      highlights = data.highlights ?? [];
    } catch (error) {
      console.error("Error loading project code:", error);
      code = "# Error loading project code\n// Please check server connection";
      structure = [];
      highlights = [];
    }
  }

  async function loadConversationHistory() {
    if (!API_URL) {
      return;
    }
    try {
      const response = await fetch(
        `${API_URL}/api/projects/${projectId}/conversation_history`
      );
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      conversationHistory = data.conversation_history || [];
    } catch (error) {
      console.error("Error loading conversation history:", error);
      conversationHistory = [];
    }
  }

  async function handleNewRequest(prompt) {
    if (!API_URL || !prompt.trim()) {
      return;
    }
    // Prevent duplicate requests
    if (isAgentLoading) {
      return;
    }
    try {
      isAgentLoading = true;
      const response = await fetch(
        `${API_URL}/api/projects/${projectId}/run_agent`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt }),
        }
      );
      if (!response.ok) {
        isAgentLoading = false;
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      // Results will be received via WebSocket (project connection)
      // isAgentLoading will be reset when agent result is received
    } catch (error) {
      isAgentLoading = false;
      console.error("Error sending new request:", error);
    }
  }

  function goHome() {
    goto("/");
  }

  async function handleStringLiteralEdit({ lineIndex, startCol, endCol, newValue }) {
    const lines = code.split("\n");
    if (lineIndex < 0 || lineIndex >= lines.length) return;
    const line = lines[lineIndex];
    const newLine = line.slice(0, startCol) + newValue + line.slice(endCol);
    lines[lineIndex] = newLine;
    const newCode = lines.join("\n");
    code = newCode;
    if (!API_URL) return;
    try {
      const r = await fetch(`${API_URL}/api/projects/${projectId}/code`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: newCode }),
      });
      if (r.ok) await loadProjectCode();
    } catch (e) {
      console.error("Failed to save string literal edit:", e);
    }
  }

  function toggleMode() {
    const newMode = mode === "edit" ? "execution" : "edit";
    if (newMode === "edit") {
      currentLine = 0;
      // Disconnect debug WebSocket when switching to edit mode
      if (wsManager.debugWs) {
        wsManager.debugWs.close();
        wsManager.debugWs = null;
        wsManager.sessionId = null;
      }
    } else {
      // Always open a fresh debug connection when switching to execution mode
      wsManager.connectDebug();
    }
    goto(`/project/${projectId}?mode=${newMode}`, { replaceState: true });
  }
</script>

<div class="header">
  <h1>Steps</h1>
  <button class="button" on:click={goHome}>Home</button>
  <button class="button" on:click={toggleMode}>
    {mode === "edit" ? "Switch to Execution" : "Switch to Edit"}
  </button>
</div>

<div class="container">
  <CodeEditor
    {code}
    {structure}
    {highlights}
    currentLine={mode === "execution" ? currentLine : 0}
    isLoading={isAgentLoading}
    {isReturnState}
    stringEditMode={mode === "edit"}
    onStringLiteralEdit={handleStringLiteralEdit}
  />
  <SidePanel {mode}>
    {#snippet historyPanel()}
      <HistoryPanel {conversationHistory} onNewRequest={handleNewRequest} />
    {/snippet}
    {#snippet executionPanel()}
      <ExecutionPanel
        {explanation}
        {isExplanationLoading}
        {variables}
        {output}
        {systemMessage}
        {canStepInto}
        {canStepOut}
        {isFinished}
      />
    {/snippet}
  </SidePanel>
</div>

<style>
  .header {
    display: flex;
    align-items: center;
    gap: var(--spacing-2xl);
    margin-bottom: var(--spacing-2xl);
  }

  .header h1 {
    margin: 0;
  }

  .container {
    display: flex;
    gap: var(--spacing-2xl);
    height: var(--container-height);
  }
</style>
