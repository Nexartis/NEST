"""
Unit tests for @mention extraction and routing.

Tests system command handling (/command) which is used for special routing:
- /help - List available commands
- /ping - Health check
- /status - Agent status information
- Unknown commands - Error handling
"""

import pytest
from unittest.mock import Mock

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
class TestSystemCommands:
    """Tests for system command handling (/command)."""

    def test_help_command(self, mock_agent_logic, sample_text_message):
        """
        Test /help command returns help text.

        /help should list all available commands.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("/help")
        response = bridge.handle_message(msg)

        response_text = response.content.text
        assert "Available commands" in response_text, \
            f"Response should contain 'Available commands', got: {response_text}"
        assert "/help" in response_text, "Response should mention /help command"
        assert "/ping" in response_text, "Response should mention /ping command"
        assert "/status" in response_text, "Response should mention /status command"

    def test_ping_command(self, mock_agent_logic, sample_text_message):
        """
        Test /ping command returns Pong.

        /ping is a simple health check that should return "Pong!"
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("/ping")
        response = bridge.handle_message(msg)

        assert "Pong!" in response.content.text, \
            f"Response should contain 'Pong!', got: {response.content.text}"

    def test_status_command(self, mock_agent_logic, sample_text_message):
        """
        Test /status command returns agent status.

        /status should show agent ID, running status, and configured URLs.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com"
        )

        msg = sample_text_message("/status")
        response = bridge.handle_message(msg)

        response_text = response.content.text
        assert "test-agent" in response_text, \
            "Response should contain agent_id 'test-agent'"
        assert "Running" in response_text, \
            "Response should contain 'Running' status"
        assert "registry.example.com" in response_text, \
            "Response should contain registry URL"

    def test_unknown_command(self, mock_agent_logic, sample_text_message):
        """
        Test unknown command returns error.

        Unrecognized commands should return an error with available commands.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("/unknown")
        response = bridge.handle_message(msg)

        assert "Unknown command" in response.content.text, \
            f"Response should indicate unknown command, got: {response.content.text}"
