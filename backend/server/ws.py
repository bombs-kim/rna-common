import json
import logging
import os
import uuid
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from settings import settings
from utils.debug import DebugSession
from server.websocket_manager import FanoutWebSocketManager

logger = logging.getLogger(__name__)

manager = FanoutWebSocketManager()

router = APIRouter()


@router.websocket("/ws/project")
async def project_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for project-level events (agent_result, etc.).
    Multiple connections allowed per project.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        message = json.loads(data)

        if message.get("type") != "connect_project":
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": "First message must be connect_project",
                    }
                )
            )
            await websocket.close()
            return

        project_id = str(message.get("project_id"))
        if not project_id:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "project_id is required"})
            )
            await websocket.close()
            return

        await manager.connect(project_id, websocket, already_accepted=True)
        await websocket.send_text(json.dumps({"type": "project_connected"}))

        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Project WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket)


@router.websocket("/ws/debug")
async def debug_websocket(websocket: WebSocket):
    """WebSocket endpoint for debug sessions. Single connection per session only."""
    await websocket.accept()
    session: DebugSession | None = None
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            message = json.loads(data)

            if message["type"] == "start_session":
                session = await handle_start_session(websocket, message)
                if not session:
                    break
                continue

            if message["type"] == "restart":
                if session is not None and not session.is_finished:
                    try:
                        session._finish()
                    except Exception:
                        pass
                session = await handle_start_session(websocket, message)
                if not session:
                    break
                await websocket.send_text(json.dumps({"type": "restart_complete"}))
                continue

            if session is None:
                raise RuntimeError("No active debug session")

            if message["type"] == "step_over":
                await handle_step_over(websocket, session, message)
            elif message["type"] == "explain_step":
                await handle_explain_step(websocket, session, message)
            elif message["type"] == "step_into":
                await handle_step_into(websocket, session, message)
            elif message["type"] == "step_out":
                await handle_step_out(websocket, session, message)
            else:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "invalid message type"})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Debug WebSocket error: {e}", exc_info=True)


async def handle_start_session(
    websocket: WebSocket, message: Dict[str, Any]
) -> DebugSession | None:
    """Create a debug session and return the DebugSession object."""
    session_id = str(uuid.uuid4())
    container_name = f"project-1-{message['project_id']}"

    user_id = "1"
    project_id = str(message["project_id"])
    filepath = (
        settings.PROJECT_CONTAINERS_DIR / user_id / project_id / "data" / "main.py"
    )

    if not filepath.exists():
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Code file not found for project {project_id}. Please generate code first.",
                    }
                )
            )
        except Exception:
            pass
        return None

    try:
        session = DebugSession(container_name)
    except Exception as e:
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Failed to start debug session: {str(e)}",
                    }
                )
            )
        except Exception:
            pass
        return None

    try:
        await websocket.send_text(
            json.dumps({"type": "session_started", "session_id": session_id})
        )
    except Exception:
        return None

    session.pdb_break("main")
    session.pdb_continue()

    state = session.get_state()
    initial_state = {
        "type": "state",
        "system_message": "session started",
        **state,
        "program_output": "",
    }
    await websocket.send_text(json.dumps(initial_state))
    return session


async def _handle_simple_command(
    websocket: WebSocket, session: DebugSession, message: Dict[str, Any], command: str
) -> None:
    """Generic step handler that executes the specified step method and returns current state."""
    if session.is_finished:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "session already finished"})
        )
        return

    getattr(session, command)()
    program_output = session.get_cumulative_program_output()

    if session.is_finished:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "finished",
                    "system_message": "session finished",
                    "program_output": program_output,
                }
            )
        )
        return

    state = session.get_state()
    system_message = "return" if state.get("is_returning", False) else ""
    state_response = {
        "type": "state",
        "system_message": system_message,
        **state,
        "program_output": program_output,
    }
    if command in ("step_out", "step_over"):
        state_response["has_explanation"] = True
    await websocket.send_text(json.dumps(state_response))


async def handle_step_into(
    websocket: WebSocket, session: DebugSession, message: Dict[str, Any]
) -> None:
    await _handle_simple_command(websocket, session, message, "step_into")


async def handle_step_out(
    websocket: WebSocket, session: DebugSession, message: Dict[str, Any]
) -> None:
    await _handle_simple_command(websocket, session, message, "step_out")


async def handle_step_over(
    websocket: WebSocket, session: DebugSession, message: Dict[str, Any]
) -> None:
    await _handle_simple_command(websocket, session, message, "step_over")


async def handle_explain_step(
    websocket: WebSocket, session: DebugSession, message: Dict[str, Any]
) -> None:
    """Generates explanation for the last step."""
    if session.is_finished:
        await websocket.send_text(
            json.dumps({"type": "error", "message": "session already finished"})
        )
        return

    try:
        explanation = session.explain_step()
        await websocket.send_text(
            json.dumps({"type": "explanation", "explanation": explanation})
        )
    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": f"Failed to generate explanation: {str(e)}",
                }
            )
        )
