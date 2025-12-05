"""
Unit tests for protocol router logic.

Tests how SimpleAgentBridge routes messages based on their prefix:
- Regular messages (no prefix) → agent_logic
- Agent-to-agent messages (@agent-id) → A2A protocol
- System commands (/command) → system handler
- MCP messages (#registry:server) → MCP handler
"""

import pytest
from unittest.mock import Mock
from python_a2a import Message, TextContent, MessageRole

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.unit
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestMessageRouting:
    """Tests for message routing based on prefix."""

    def test_regular_message_calls_agent_logic(self, mock_agent_logic, sample_text_message):
        """
        Regular message (no prefix) should call agent_logic.

        Messages without @, #, or / prefix are treated as regular messages
        and passed to the agent_logic callback for LLM processing.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("Hello, how are you?")
        response = bridge.handle_message(msg)

        assert response.role == MessageRole.AGENT, \
            f"Response role should be AGENT, got {response.role}"
        assert "Response to: Hello, how are you?" in response.content.text, \
            f"Response should contain agent_logic output, got: {response.content.text}"

    def test_regular_message_includes_agent_id(self, mock_agent_logic, sample_text_message):
        """
        Response should include agent ID prefix.

        All responses are formatted as "[agent_id] response_text"
        """
        bridge = SimpleAgentBridge(
            agent_id="my-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("Test message")
        response = bridge.handle_message(msg)

        assert "[my-agent]" in response.content.text, \
            f"Response should include '[my-agent]', got: {response.content.text}"

    def test_regular_message_logs_telemetry(self, mock_agent_logic, mock_telemetry, sample_text_message):
        """
        Regular message should log to telemetry.

        When telemetry is configured, log_message_received should be called.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic,
            telemetry=mock_telemetry
        )

        msg = sample_text_message("Hello")
        bridge.handle_message(msg)

        mock_telemetry.log_message_received.assert_called_once()
