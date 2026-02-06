/**
 * WebSocket Manager - ES6 Module version
 * Manages both project-level and debug session WebSocket connections
 */

const API_URL = import.meta.env.VITE_API_URL;
const getProjectWSUrl = () => API_URL ? API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/project' : null;
const getDebugWSUrl = () => API_URL ? API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/debug' : null;

class WebSocketManager {
  constructor() {
    this.projectWs = null;  // Project-level connection (for agent_result)
    this.debugWs = null;    // Debug session connection (for debug messages)
    this.projectId = null;
    this.handlers = {
      updateStatus: null,
      handleStepResult: null,
      handleState: null,
      handleRestart: null,
      updateSystemMessageDisplay: null,
      handleAgentResult: null,
      handleExplanation: null,
      handleFinished: null
    };
  }

  setHandlers(handlers) {
    this.handlers = { ...this.handlers, ...handlers };
  }

  connectProject(projectIdParam) {
    this.projectId = projectIdParam;
    const WS_URL = getProjectWSUrl();
    if (!WS_URL) {
      console.error('VITE_API_URL is not set');
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus('Error: VITE_API_URL not configured');
      }
      return;
    }

    if (this.projectWs) {
      this.projectWs.close();
      this.projectWs = null;
    }

    this.projectWs = new WebSocket(WS_URL);

    this.projectWs.onopen = () => {
      // Send connect_project message
      const connectMessage = {
        type: "connect_project",
        project_id: parseInt(this.projectId),
      };
      this.projectWs.send(JSON.stringify(connectMessage));
    };

    this.projectWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleProjectMessage(data);
    };

    this.projectWs.onclose = () => {
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Project connection disconnected");
      }
    };

    this.projectWs.onerror = (error) => {
      console.error("Project WebSocket error:", error);
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Project WebSocket error: " + error);
      }
    };
  }

  connectDebug() {
    const WS_URL = getDebugWSUrl();
    if (!WS_URL) {
      console.error('VITE_API_URL is not set');
      return;
    }

    if (this.debugWs) {
      this.debugWs.close();
      this.debugWs = null;
    }

    this.debugWs = new WebSocket(WS_URL);

    this.debugWs.onopen = () => {
      // Start debug session with project ID
      const startMessage = {
        type: "start_session",
        project_id: parseInt(this.projectId),
      };
      this.debugWs.send(JSON.stringify(startMessage));
    };

    this.debugWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleDebugMessage(data);
    };

    this.debugWs.onclose = () => {
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug connection disconnected");
      }
    };

    this.debugWs.onerror = (error) => {
      console.error("Debug WebSocket error:", error);
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug WebSocket error: " + error);
      }
    };
  }

  disconnect() {
    if (this.projectWs) {
      this.projectWs.close();
      this.projectWs = null;
    }
    if (this.debugWs) {
      this.debugWs.close();
      this.debugWs = null;
    }
  }

  handleProjectMessage(data) {
    switch (data.type) {
      case "project_connected":
        if (this.handlers.updateStatus) {
          this.handlers.updateStatus("Project connected");
        }
        break;
      case "agent_result":
        if (this.handlers.handleAgentResult) {
          this.handlers.handleAgentResult(data);
        }
        break;
      default:
        console.warn("Unknown project message type:", data.type);
    }
  }

  handleDebugMessage(data) {
    switch (data.type) {
      case "session_started":
        if (this.handlers.updateStatus) {
          this.handlers.updateStatus("Debug session started");
        }
        break;
      case "step_result":
        if (this.handlers.handleStepResult) {
          this.handlers.handleStepResult(data);
        }
        break;
      case "state":
        if (this.handlers.handleState) {
          this.handlers.handleState(data);
        }
        // Automatically request explanation if flag is set (for step_over)
        if (data.has_explanation) {
          this.explainStep();
        }
        break;
      case "explanation":
        if (this.handlers.handleExplanation) {
          this.handlers.handleExplanation(data);
        }
        break;
      case "restart_complete":
        if (this.handlers.handleRestart) {
          this.handlers.handleRestart();
        }
        break;
      case "finished":
        if (this.handlers.updateStatus) {
          this.handlers.updateStatus("Program execution finished");
        }
        if (this.handlers.handleFinished) {
          this.handlers.handleFinished(data);
        }
        break;
      case "error":
        if (this.handlers.updateStatus) {
          this.handlers.updateStatus("Error: " + data.message);
        }
        console.error("Server error:", data.message);
        break;
      default:
        console.warn("Unknown debug message type:", data.type);
    }
  }

  // Legacy method for backwards compatibility
  connect(projectIdParam) {
    this.connectProject(projectIdParam);
    this.connectDebug();
  }

  stepOver() {
    if (this.debugWs && this.debugWs.readyState === WebSocket.OPEN) {
      const message = {
        type: "step_over",
      };
      this.debugWs.send(JSON.stringify(message));
    } else {
      console.error("Debug WebSocket not connected");
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug WebSocket not connected");
      }
    }
  }

  stepInto() {
    if (this.debugWs && this.debugWs.readyState === WebSocket.OPEN) {
      const message = {
        type: "step_into",
      };
      this.debugWs.send(JSON.stringify(message));
    } else {
      console.error("Debug WebSocket not connected");
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug WebSocket not connected");
      }
    }
  }

  stepOut() {
    if (this.debugWs && this.debugWs.readyState === WebSocket.OPEN) {
      const message = {
        type: "step_out",
      };
      this.debugWs.send(JSON.stringify(message));
    } else {
      console.error("Debug WebSocket not connected");
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug WebSocket not connected");
      }
    }
  }

  restart() {
    if (this.debugWs && this.debugWs.readyState === WebSocket.OPEN) {
      const message = {
        type: "restart",
        project_id: parseInt(this.projectId),
      };
      this.debugWs.send(JSON.stringify(message));
    } else {
      console.error("Debug WebSocket not connected");
      if (this.handlers.updateStatus) {
        this.handlers.updateStatus("Debug WebSocket not connected");
      }
    }
  }

  explainStep() {
    if (this.debugWs && this.debugWs.readyState === WebSocket.OPEN) {
      const message = {
        type: "explain_step",
      };
      this.debugWs.send(JSON.stringify(message));
    } else {
      console.error("Debug WebSocket not connected");
    }
  }
}

// Export singleton instance
export const wsManager = new WebSocketManager();
export default wsManager;
