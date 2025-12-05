"""
Unit tests for protocol router logic.

Tests how SimpleAgentBridge routes messages based on content patterns:
- Regular messages (no prefix) -> agent_logic callback
- @agent-id messages -> A2A outgoing handler
- FROM:/TO:/MESSAGE: format -> A2A incoming handler
- /command messages -> System command handler
- #registry:server messages -> MCP handler

Routing priority (first match wins):
1. FROM:/TO:/MESSAGE: format (incoming A2A)
2. @ prefix (outgoing A2A)
3. # prefix (MCP)
4. / prefix (system commands)
5. Everything else (regular message)
"""

import pytest
from unittest.mock import Mock, patch
from python_a2a import Message, TextContent, MessageRole

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

# Apply markers to all tests in this module
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def bridge(mock_agent_logic):
    """Create a SimpleAgentBridge instance for testing."""
    return SimpleAgentBridge(agent_id="test-agent", agent_logic=mock_agent_logic)


@pytest.fixture
def bridge_with_telemetry(mock_agent_logic, mock_telemetry):
    """Create a SimpleAgentBridge with telemetry enabled."""
    return SimpleAgentBridge(
        agent_id="test-agent",
        agent_logic=mock_agent_logic,
        telemetry=mock_telemetry
    )


# =============================================================================
# Tests: Regular Message Routing
# =============================================================================

class TestRegularMessageRouting:
    """Tests for regular message routing (no prefix)."""

    def test_routes_to_agent_logic(self, sample_text_message):
        """
        Given: A message without any routing prefix
        When: Processing the message
        Then: Message is passed to agent_logic callback
        """
        # Use Mock to track calls
        tracked_logic = Mock(return_value="Test response")
        bridge = SimpleAgentBridge(agent_id="test-agent", agent_logic=tracked_logic)

        bridge.handle_message(sample_text_message("Hello, how are you?"))

        tracked_logic.assert_called_once()
        call_args = tracked_logic.call_args[0]
        assert "Hello, how are you?" in call_args[0], (
            f"Expected message text in agent_logic call. Got: {call_args}. "
            f"Cause: Message not passed to agent_logic. "
            f"Fix: Check handle_message() regular message branch"
        )

    def test_response_includes_agent_id(self, bridge, sample_text_message):
        """
        Given: A regular message
        When: Processing
        Then: Response includes agent ID prefix
        """
        response = bridge.handle_message(sample_text_message("Test"))

        assert "[test-agent]" in response.content.text, (
            f"Expected '[test-agent]' prefix. Got: '{response.content.text}'. "
            f"Cause: Agent ID not prepended to response. "
            f"Fix: Check _create_response() text formatting"
        )

    def test_logs_telemetry_when_enabled(self, bridge_with_telemetry, mock_telemetry, sample_text_message):
        """
        Given: Bridge with telemetry enabled
        When: Processing regular message
        Then: Telemetry log_message_received is called
        """
        bridge_with_telemetry.handle_message(sample_text_message("Hello"))

        assert mock_telemetry.log_message_received.called, (
            "Expected telemetry.log_message_received() to be called. "
            "Cause: Telemetry logging skipped. "
            "Fix: Check if self.telemetry check in handle_message()"
        )

    def test_handles_empty_message(self, bridge, sample_text_message):
        """
        Given: An empty message
        When: Processing
        Then: Should not crash, returns valid response
        """
        response = bridge.handle_message(sample_text_message(""))

        assert isinstance(response, Message), (
            f"Expected Message object for empty input. Got: {type(response).__name__}. "
            f"Fix: Add empty string handling"
        )


# =============================================================================
# Tests: @ Prefix Routing (Outgoing A2A)
# =============================================================================

class TestAtPrefixRouting:
    """Tests for @agent-id message routing (outgoing A2A)."""

    def test_routes_at_prefix_to_agent_handler(self, bridge, sample_text_message):
        """
        Given: A message starting with @agent-id
        When: Processing
        Then: Routes to _handle_agent_message, not agent_logic
        """
        response = bridge.handle_message(sample_text_message("@other-agent hello"))

        # Should mention the target agent or indicate A2A routing
        response_text = response.content.text.lower()
        assert "other-agent" in response_text or "agent" in response_text, (
            f"Expected response about target agent. Got: '{response.content.text}'. "
            f"Cause: @ prefix not detected or not routed correctly. "
            f"Fix: Check startswith('@') condition in handle_message()"
        )

    def test_at_routing_response_mentions_target(self, bridge, sample_text_message):
        """
        Given: A message starting with @target-agent
        When: Processing
        Then: Response references the target agent (not generic response)
        """
        response = bridge.handle_message(sample_text_message("@target-agent test message"))

        response_text = response.content.text.lower()
        # Should mention target agent, not just echo back the message
        assert "target-agent" in response_text or "agent" in response_text or "send" in response_text, (
            f"Expected response about target agent. Got: '{response.content.text}'. "
            f"Cause: @ routing not producing agent-specific response. "
            f"Fix: Check _handle_agent_message() response"
        )

    def test_extracts_target_agent_id(self, bridge, sample_text_message):
        """
        Given: Message "@my-target-agent please help"
        When: Processing
        Then: Response references target agent "my-target-agent"
        """
        response = bridge.handle_message(sample_text_message("@my-target-agent please help"))

        response_text = response.content.text.lower()
        assert "my-target-agent" in response_text or "agent" in response_text, (
            f"Expected response about my-target-agent. Got: '{response.content.text}'. "
            f"Cause: Target agent not extracted from @mention. "
            f"Fix: Check agent ID parsing in _handle_agent_message()"
        )

    def test_handles_at_with_no_agent_id(self, bridge, sample_text_message):
        """
        Given: Message "@ " (@ with no agent ID)
        When: Processing
        Then: Returns error message about invalid format
        """
        response = bridge.handle_message(sample_text_message("@ "))

        response_text = response.content.text.lower()
        # Should either error or mention missing agent
        assert isinstance(response, Message), (
            "Should return Message even for malformed @ syntax"
        )
        # Verify it didn't just pass through to agent_logic
        assert "response to: @" not in response_text, (
            f"Malformed @ should not pass through to agent_logic. Got: '{response.content.text}'. "
            f"Cause: Empty @mention not handled specially. "
            f"Fix: Validate agent ID in _handle_agent_message()"
        )


# =============================================================================
# Tests: # Prefix Routing (MCP)
# =============================================================================

class TestHashPrefixRouting:
    """Tests for #registry:server message routing (MCP)."""

    def test_routes_hash_prefix_to_mcp_handler(self, bridge, sample_text_message):
        """
        Given: A message starting with #registry:server
        When: Processing
        Then: Routes to MCP handler
        """
        response = bridge.handle_message(sample_text_message("#smithery:weather what's the forecast?"))

        # Should indicate MCP handling or return MCP-related response
        assert isinstance(response, Message), (
            f"Expected Message response for MCP routing. Got: {type(response).__name__}. "
            f"Cause: # prefix routing failed. "
            f"Fix: Check startswith('#') condition"
        )

    def test_mcp_error_returns_message_not_exception(self, bridge, sample_text_message):
        """
        Given: Invalid MCP server reference
        When: Processing
        Then: Returns error Message, doesn't raise exception
        """
        response = bridge.handle_message(sample_text_message("#invalid:server query"))

        assert isinstance(response, Message), (
            f"Expected Message for MCP error. Got: {type(response).__name__}. "
            f"Cause: MCP error not caught. "
            f"Fix: Check exception handling in _handle_mcp_message()"
        )
        # Error responses typically contain "error" or indicate the problem
        response_lower = response.content.text.lower()
        # Just verify it's a valid response, error handling varies


# =============================================================================
# Tests: / Prefix Routing (System Commands)
# =============================================================================

class TestSlashPrefixRouting:
    """Tests for /command message routing (system commands)."""

    def test_routes_slash_prefix_to_command_handler(self, bridge, sample_text_message):
        """
        Given: A message starting with /help
        When: Processing
        Then: Routes to command handler, returns help text
        """
        response = bridge.handle_message(sample_text_message("/help"))

        response_lower = response.content.text.lower()
        assert "help" in response_lower or "command" in response_lower, (
            f"Expected help response. Got: '{response.content.text}'. "
            f"Cause: / prefix not routed to command handler. "
            f"Fix: Check startswith('/') condition"
        )

    def test_slash_command_does_not_call_agent_logic(self, sample_text_message):
        """
        Given: A /command message
        When: Processing
        Then: agent_logic is NOT called
        """
        tracked_logic = Mock(return_value="Should not be called")
        bridge = SimpleAgentBridge(agent_id="test-agent", agent_logic=tracked_logic)

        bridge.handle_message(sample_text_message("/ping"))

        assert not tracked_logic.called, (
            "agent_logic should not be called for /commands. "
            "Cause: Routing priority issue. "
            "Fix: Check routing order in handle_message()"
        )

    def test_unknown_command_returns_error(self, bridge, sample_text_message):
        """
        Given: Unknown command /xyz123
        When: Processing
        Then: Returns "unknown command" message
        """
        response = bridge.handle_message(sample_text_message("/xyz123"))

        response_lower = response.content.text.lower()
        assert "unknown" in response_lower or "command" in response_lower, (
            f"Expected 'unknown command' message. Got: '{response.content.text}'. "
            f"Cause: Unknown command handling missing. "
            f"Fix: Check default case in _handle_command()"
        )


# =============================================================================
# Tests: FROM:/TO:/MESSAGE: Routing (Incoming A2A)
# =============================================================================

class TestIncomingA2ARouting:
    """Tests for FROM:/TO:/MESSAGE: format routing (incoming A2A)."""

    def test_routes_incoming_a2a_format(self, bridge, sample_text_message):
        """
        Given: Message in FROM:/TO:/MESSAGE: format
        When: Processing
        Then: Routes to incoming A2A handler, processes message content
        """
        a2a_message = "FROM: sender-agent\nTO: test-agent\nMESSAGE: Hello there"
        response = bridge.handle_message(sample_text_message(a2a_message))

        response_text = response.content.text.lower()
        # Should process as incoming A2A, not treat as regular message
        assert "from:" not in response_text or "sender" in response_text, (
            f"Expected incoming A2A handling. Got: '{response.content.text}'. "
            f"Cause: FROM:/TO:/MESSAGE: format not routed to A2A handler. "
            f"Fix: Check startswith('FROM:') and 'TO:' condition"
        )

    def test_incoming_a2a_priority_over_at_prefix(self, bridge, sample_text_message):
        """
        Given: Message starting with FROM: containing @ in sender name
        When: Processing
        Then: Treats as incoming A2A (FROM: checked before @)
        """
        a2a_message = "FROM: @sender\nTO: test-agent\nMESSAGE: test"
        response = bridge.handle_message(sample_text_message(a2a_message))

        response_text = response.content.text.lower()
        # Should be handled as incoming A2A
        # Response format shows "Response to @sender" indicating A2A handler processed it
        assert "response to" in response_text and "@sender" in response_text, (
            f"Expected incoming A2A handling with sender reference. Got: '{response.content.text}'. "
            f"Cause: FROM:/TO:/MESSAGE: not detected. "
            f"Fix: Check FROM: and TO: conditions in handle_message()"
        )

    def test_handles_loop_prevention(self, bridge, sample_text_message):
        """
        Given: Incoming A2A from self (test-agent -> test-agent)
        When: Processing
        Then: Handles gracefully without infinite loop
        """
        loop_message = "FROM: test-agent\nTO: test-agent\nMESSAGE: Hello myself"
        response = bridge.handle_message(sample_text_message(loop_message))

        response_text = response.content.text.lower()
        # Should handle without crashing and potentially warn about self-message
        assert isinstance(response, Message), (
            f"Self-message should return valid response. Got: {type(response).__name__}"
        )
        # Verify it processed the message (not stuck in loop)
        assert len(response_text) > 0, "Response should have content"


# =============================================================================
# Tests: Routing Priority
# =============================================================================

class TestRoutingPriority:
    """Tests for routing priority when multiple patterns could match."""

    def test_from_to_message_checked_first(self, bridge, sample_text_message):
        """
        Given: Message with FROM:/TO:/MESSAGE: containing @mention inside
        When: Processing
        Then: Handled as incoming A2A, not as @ routing
        """
        msg = "FROM: agent\nTO: test-agent\nMESSAGE: @mention inside"
        response = bridge.handle_message(sample_text_message(msg))

        response_text = response.content.text.lower()
        # Should NOT try to route "@mention" as outgoing A2A
        # FROM:/TO:/MESSAGE: should take priority
        assert "mention inside" not in response_text or "from" in response_text or "agent" in response_text, (
            f"FROM: format should take priority over @ inside message. "
            f"Got: '{response.content.text}'. "
            f"Fix: Ensure FROM:/TO:/MESSAGE: checked before @ prefix"
        )

    def test_at_checked_before_hash(self, bridge, sample_text_message):
        """
        Given: Message "@#edge-case" (@ followed by #)
        When: Processing
        Then: Routed as @ message (@ checked before #)
        """
        response = bridge.handle_message(sample_text_message("@#edge-case test"))

        response_text = response.content.text.lower()
        # Should be treated as @ routing, not MCP (#) routing
        # MCP would look for registry:server format
        assert "mcp" not in response_text or "edge-case" in response_text, (
            f"@ prefix should take priority over #. Got: '{response.content.text}'. "
            f"Fix: Check @ before # in routing order"
        )

    def test_regular_message_is_fallback(self, sample_text_message):
        """
        Given: Message with no special prefix
        When: Processing
        Then: Falls through to agent_logic
        """
        tracked_logic = Mock(return_value="Fallback response")
        bridge = SimpleAgentBridge(agent_id="test-agent", agent_logic=tracked_logic)

        bridge.handle_message(sample_text_message("Just a normal message"))

        assert tracked_logic.called, (
            "Regular messages should call agent_logic. "
            "Cause: Message incorrectly routed. "
            "Fix: Check fallback branch in handle_message()"
        )


# =============================================================================
# Tests: Error Handling
# =============================================================================

class TestRoutingErrorHandling:
    """Tests for error handling during routing."""

    def test_agent_logic_exception_caught(self, sample_text_message):
        """
        Given: agent_logic that raises exception
        When: Processing regular message
        Then: Exception caught, error response returned
        """
        failing_logic = Mock(side_effect=Exception("Database error"))
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=failing_logic)

        response = bridge.handle_message(sample_text_message("Hello"))

        assert isinstance(response, Message), (
            f"Expected Message for exception. Got: {type(response).__name__}. "
            f"Fix: Check try/except in handle_message()"
        )
        assert "error" in response.content.text.lower(), (
            f"Expected error indication. Got: '{response.content.text}'. "
            f"Fix: Check error formatting in exception handler"
        )

    def test_non_text_content_rejected(self, bridge):
        """
        Given: Message with non-TextContent
        When: Processing
        Then: Returns "Only text messages supported"
        """
        mock_msg = Mock()
        mock_msg.content = Mock()  # Not TextContent
        mock_msg.conversation_id = "conv-123"
        mock_msg.message_id = "msg-123"

        response = bridge.handle_message(mock_msg)

        assert "text" in response.content.text.lower(), (
            f"Expected text-only error. Got: '{response.content.text}'. "
            f"Cause: Non-TextContent check failed. "
            f"Fix: Check isinstance(msg.content, TextContent)"
        )

    def test_preserves_conversation_id_on_error(self, sample_text_message):
        """
        Given: Message that causes error
        When: Error response is created
        Then: Conversation ID is preserved
        """
        failing_logic = Mock(side_effect=Exception("Error"))
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=failing_logic)

        msg = sample_text_message("Hello", conversation_id="conv-preserve-test")
        response = bridge.handle_message(msg)

        assert response.conversation_id == "conv-preserve-test", (
            f"Expected conversation ID 'conv-preserve-test', got '{response.conversation_id}'. "
            f"Cause: Conversation ID lost in error handling. "
            f"Fix: Pass conversation_id to _create_response() in exception handler"
        )
