"""
Integration tests for protocol communication flows.

Tests agent-to-agent communication, MCP protocol handling, and incoming messages
with mocked external agents.
"""

import pytest
from unittest.mock import Mock, patch

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.integration
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestAgentToAgentCommunication:
    """Tests for agent-to-agent message handling (@agent-id)."""

    def test_agent_message_format_validation(self, mock_agent_logic, sample_text_message):
        """
        Test that @agent without message returns error.

        Format should be "@agent-id message", not just "@agent-id"
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("@other-agent")
        response = bridge.handle_message(msg)

        assert "Invalid format" in response.content.text, \
            f"Response should indicate invalid format, got: {response.content.text}"

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_agent_message_lookup_and_send(
        self, mock_a2a_client, mock_requests, mock_agent_logic, sample_text_message
    ):
        """
        Test that @agent message looks up agent and sends message.

        Flow: Parse @target -> Lookup in registry -> Send via A2A -> Return response
        """
        # Mock registry lookup
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"agent_url": "http://other-agent:6001"}
        mock_requests.return_value = mock_response

        # Mock A2A client response
        mock_client_instance = Mock()
        mock_a2a_response = Mock()
        mock_a2a_response.parts = [Mock(text="Hello from other agent")]
        mock_client_instance.send_message.return_value = mock_a2a_response
        mock_a2a_client.return_value = mock_client_instance

        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com"
        )

        msg = sample_text_message("@other-agent Hello there!")
        response = bridge.handle_message(msg)

        # Verify registry was called
        mock_requests.assert_called_once()
        call_url = mock_requests.call_args[0][0]
        assert "other-agent" in call_url, \
            f"Registry lookup should include target agent, got: {call_url}"

    def test_agent_not_found(self, mock_agent_logic, sample_text_message):
        """
        Test message to non-existent agent.

        When target agent is not in registry, should return "not found" error.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
            # No registry_url, so lookup will fail
        )

        msg = sample_text_message("@nonexistent-agent Hello")
        response = bridge.handle_message(msg)

        assert "not found" in response.content.text.lower(), \
            f"Response should indicate agent not found, got: {response.content.text}"


@pytest.mark.integration
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestMCPProtocol:
    """Tests for MCP message handling (#registry:server)."""

    def test_mcp_message_without_registry(self, mock_agent_logic, sample_text_message):
        """
        Test MCP message without MCP registry configured.

        When using #nanda:server without mcp_registry_url, should return config error.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
            # No mcp_registry_url
        )

        msg = sample_text_message("#nanda:test-server get data")
        response = bridge.handle_message(msg)

        response_lower = response.content.text.lower()
        # Should return error about MCP not available or not configured
        assert "mcp" in response_lower or "error" in response_lower or "not configured" in response_lower, \
            f"Response should indicate MCP issue, got: {response.content.text}"

    def test_mcp_message_invalid_format(self, mock_agent_logic, sample_text_message):
        """
        Test MCP message with invalid format.

        Valid format: #registry:server-name query
        Invalid: #invalid-format (missing colon separator)
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic,
            mcp_registry_url="http://mcp.example.com"
        )

        msg = sample_text_message("#invalid-format")
        response = bridge.handle_message(msg)

        response_lower = response.content.text.lower()
        # Should return format error
        assert "invalid" in response_lower or "format" in response_lower or "error" in response_lower, \
            f"Response should indicate format error, got: {response.content.text}"


@pytest.mark.integration
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestIncomingAgentMessages:
    """Tests for handling incoming messages from other agents."""

    def test_incoming_agent_message_format(self, mock_agent_logic, sample_text_message):
        """
        Test parsing of incoming agent message format.

        Incoming format: "FROM: sender\nTO: receiver\nMESSAGE: content"
        """
        incoming_msg = "FROM: sender-agent\nTO: test-agent\nMESSAGE: Hello from sender"

        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message(incoming_msg)
        response = bridge.handle_message(msg)

        # Should process and respond
        assert "Response to sender-agent" in response.content.text, \
            f"Response should acknowledge sender, got: {response.content.text}"

    def test_incoming_reply_no_loop(self, mock_agent_logic, sample_text_message):
        """
        Test that replies don't trigger infinite loops.

        When receiving a reply (starts with "Response to"), should not respond back.
        """
        incoming_reply = "FROM: other-agent\nTO: test-agent\nMESSAGE: Response to test-agent: Here's your answer"

        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message(incoming_reply)
        response = bridge.handle_message(msg)

        # Should display but not respond back
        assert "[other-agent]" in response.content.text, \
            f"Response should display sender, got: {response.content.text}"
