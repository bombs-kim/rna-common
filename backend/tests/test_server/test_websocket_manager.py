"""
Tests for FanoutWebSocketManager class.

Tests cover:
- Project-level connections (1:N - multiple connections per project)
- Message sending
- Connection cleanup
"""

from unittest.mock import AsyncMock

import pytest

from server.websocket_manager import FanoutWebSocketManager


class TestFanoutWebSocketManager:
    """Test suite for FanoutWebSocketManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh FanoutWebSocketManager instance for each test."""
        return FanoutWebSocketManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket object."""
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    # Project Connection Tests (1:N)

    @pytest.mark.asyncio
    async def test_connect_project_single_connection(self, manager, mock_websocket):
        """Test connecting a single project-level connection."""
        project_id = "1"

        await manager.connect(project_id, mock_websocket)

        assert project_id in manager.project_connections
        assert len(manager.project_connections[project_id]) == 1
        assert mock_websocket in manager.project_connections[project_id]
        assert manager.websocket_projects[mock_websocket] == project_id
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_project_multiple_connections(self, manager, mock_websocket):
        """Test connecting multiple connections for the same project (1:N)."""
        project_id = "1"
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(project_id, ws1)
        await manager.connect(project_id, ws2)

        assert project_id in manager.project_connections
        assert len(manager.project_connections[project_id]) == 2
        assert ws1 in manager.project_connections[project_id]
        assert ws2 in manager.project_connections[project_id]
        assert manager.websocket_projects[ws1] == project_id
        assert manager.websocket_projects[ws2] == project_id

    @pytest.mark.asyncio
    async def test_connect_project_already_accepted(self, manager, mock_websocket):
        """Test connecting project when websocket is already accepted."""
        project_id = "1"

        await manager.connect(project_id, mock_websocket, already_accepted=True)

        assert project_id in manager.project_connections
        mock_websocket.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_project(self, manager, mock_websocket):
        """Test disconnecting a project-level connection."""
        project_id = "1"
        await manager.connect(project_id, mock_websocket, already_accepted=True)

        manager.disconnect(mock_websocket)

        assert project_id not in manager.project_connections
        assert mock_websocket not in manager.websocket_projects

    @pytest.mark.asyncio
    async def test_disconnect_project_multiple_connections(self, manager):
        """Test disconnecting one connection when multiple exist."""
        project_id = "1"
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(project_id, ws1, already_accepted=True)
        await manager.connect(project_id, ws2, already_accepted=True)

        manager.disconnect(ws1)

        assert project_id in manager.project_connections
        assert len(manager.project_connections[project_id]) == 1
        assert ws2 in manager.project_connections[project_id]
        assert ws1 not in manager.project_connections[project_id]

    @pytest.mark.asyncio
    async def test_send_to_project(self, manager):
        """Test sending message to all connections for a project."""
        project_id = "1"
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(project_id, ws1, already_accepted=True)
        await manager.connect(project_id, ws2, already_accepted=True)

        message = '{"type": "test"}'
        await manager.send_to(project_id, message)

        ws1.send_text.assert_called_once_with(message)
        ws2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_project_handles_disconnected(self, manager):
        """Test that disconnected websockets are cleaned up when sending fails."""
        project_id = "1"
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock(side_effect=Exception("Connection closed"))
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(project_id, ws1, already_accepted=True)
        await manager.connect(project_id, ws2, already_accepted=True)

        message = '{"type": "test"}'
        await manager.send_to(project_id, message)

        # ws1 should be removed, ws2 should still be there
        assert ws1 not in manager.project_connections[project_id]
        assert ws2 in manager.project_connections[project_id]
        ws2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_project_nonexistent(self, manager):
        """Test sending to a project with no connections."""
        project_id = "999"
        message = '{"type": "test"}'

        # Should not raise an exception
        await manager.send_to(project_id, message)

    # Integration Tests

    @pytest.mark.asyncio
    async def test_multiple_projects_independent(self, manager):
        """Test that different projects maintain independent connections."""
        project1 = "1"
        project2 = "2"
        ws1 = AsyncMock()
        ws1.send_text = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_text = AsyncMock()

        await manager.connect(project1, ws1, already_accepted=True)
        await manager.connect(project2, ws2, already_accepted=True)

        assert project1 in manager.project_connections
        assert project2 in manager.project_connections
        assert len(manager.project_connections[project1]) == 1
        assert len(manager.project_connections[project2]) == 1

        message = '{"type": "test"}'
        await manager.send_to(project1, message)

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()
