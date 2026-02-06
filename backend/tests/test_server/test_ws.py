"""
Basic tests for WebSocket endpoints in server.ws.
"""

import json

from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


class TestProjectWebSocket:
    def test_error_when_first_message_not_connect_project(self):
        with client.websocket_connect("/ws/project") as ws:
            ws.send_text(json.dumps({"type": "other"}))
            data = json.loads(ws.receive_text())
        assert data["type"] == "error"
        assert "connect_project" in data["message"].lower()

    def test_error_when_project_id_empty(self):
        with client.websocket_connect("/ws/project") as ws:
            ws.send_text(json.dumps({"type": "connect_project", "project_id": ""}))
            data = json.loads(ws.receive_text())
        assert data["type"] == "error"
        assert "project_id" in data["message"].lower()

    def test_project_connected_when_valid_connect_project(self):
        with client.websocket_connect("/ws/project") as ws:
            ws.send_text(json.dumps({"type": "connect_project", "project_id": "1"}))
            data = json.loads(ws.receive_text())
        assert data["type"] == "project_connected"
