"""
Shared pytest fixtures for NEST tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from python_a2a import Message, TextContent, MessageRole


@pytest.fixture
def mock_agent_logic():
    """Mock agent logic function that returns a simple response."""
    def agent_logic(message: str, conversation_id: str) -> str:
        return f"Response to: {message}"
    return agent_logic


@pytest.fixture
def mock_telemetry():
    """Mock telemetry system."""
    telemetry = Mock()
    telemetry.log_message_received = Mock()
    telemetry.log_message_sent = Mock()
    return telemetry


@pytest.fixture
def sample_text_message():
    """Create a sample text message for testing."""
    def _create_message(text: str, conversation_id: str = "test-conv-123"):
        return Message(
            role=MessageRole.USER,
            content=TextContent(text=text),
            conversation_id=conversation_id
        )
    return _create_message


@pytest.fixture
def mock_registry_response():
    """Mock response from agent registry lookup."""
    return {
        "agent_id": "test-agent",
        "agent_url": "http://localhost:6001",
        "name": "Test Agent",
        "status": "active"
    }


@pytest.fixture
def mock_requests_get():
    """Patch requests.get for registry lookups."""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_a2a_client():
    """Mock A2A client for agent-to-agent communication."""
    with patch('nanda_core.core.agent_bridge.A2AClient') as mock_client:
        yield mock_client
