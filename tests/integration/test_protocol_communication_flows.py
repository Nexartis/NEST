"""
Integration tests for protocol communication flows.

Tests A2A (Agent-to-Agent) communication with mocked external services:
- Agent lookup via registry
- Message sending via A2A protocol
- Response handling and formatting
- Error scenarios (not found, timeout, network errors)

Test Organization:
- TestA2AMessageFormatValidation: Format parsing and validation
- TestRegistryLookupBehavior: Registry HTTP interactions
- TestA2AMessageSending: Outbound A2A communication
- TestIncomingA2AMessageHandling: Inbound message parsing
- TestMessageMetadataPreservation: Conversation ID tracking
- TestA2AEdgeCasesAndBoundaries: Boundary conditions and special inputs
"""

import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, ConnectionError

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    from python_a2a import Message, MessageRole, TextContent
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

# Apply markers to all tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def bridge_with_registry(mock_agent_logic):
    """Bridge configured with registry URL for agent lookup."""
    return SimpleAgentBridge(
        agent_id="test-agent",
        agent_logic=mock_agent_logic,
        registry_url="http://registry.example.com"
    )


@pytest.fixture
def bridge_without_registry(mock_agent_logic):
    """Bridge without registry URL - cannot lookup agents."""
    return SimpleAgentBridge(
        agent_id="test-agent",
        agent_logic=mock_agent_logic
    )


@pytest.fixture
def mock_registry_response():
    """Factory for creating mock registry responses."""
    def _create(status_code: int, json_data: dict = None, raise_for_status=None):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        if raise_for_status:
            mock_response.raise_for_status.side_effect = raise_for_status
        return mock_response
    return _create


@pytest.fixture
def mock_a2a_client():
    """Factory for creating mock A2A client with configurable responses."""
    def _create(response_text: str = None, error: Exception = None, parts: list = None):
        mock_client = Mock()
        if error:
            mock_client.send_message.side_effect = error
        else:
            mock_response = Mock()
            if parts is not None:
                mock_response.parts = parts
            elif response_text:
                mock_response.parts = [Mock(text=response_text)]
            else:
                mock_response.parts = []
            mock_client.send_message.return_value = mock_response
        return mock_client
    return _create


# =============================================================================
# Helper Functions
# =============================================================================

def assert_error_response(response, expected_keywords: list, context: str):
    """
    Assert response indicates an error with helpful diagnostics.

    Args:
        response: The Message response to check
        expected_keywords: List of keywords that should appear (any one match = pass)
        context: Description of what was being tested
    """
    assert isinstance(response, Message), (
        f"Expected Message response for {context}. Got crash. "
        f"Cause: Exception not caught. "
        f"Fix: Add try-except in message handler"
    )
    response_lower = response.content.text.lower()
    matched = any(kw in response_lower for kw in expected_keywords)
    assert matched, (
        f"Expected one of {expected_keywords} in response for {context}. "
        f"Got: '{response.content.text}'. "
        f"Cause: Error not converted to user-friendly message. "
        f"Fix: Return descriptive error message"
    )


# =============================================================================
# Tests: A2A Message Format Validation
# =============================================================================

class TestA2AMessageFormatValidation:
    """Tests for @agent-id message format parsing and validation."""

    def test_bare_mention_without_body_returns_invalid_format(
        self, bridge_with_registry, sample_text_message
    ):
        """
        Given: "@target-agent" with no message body
        When: Processing the message
        Then: Returns "Invalid format" error (not routing attempt)

        Why: Bare mentions are ambiguous - user must provide a message to send.
        """
        response = bridge_with_registry.handle_message(sample_text_message("@target-agent"))

        assert "Invalid format" in response.content.text, (
            f"Expected 'Invalid format' for bare @mention. "
            f"Got: '{response.content.text}'. "
            f"Cause: No validation for empty message body. "
            f"Fix: Check for non-empty body after parsing agent ID"
        )

    def test_valid_mention_with_body_attempts_routing(
        self, bridge_without_registry, sample_text_message
    ):
        """
        Given: "@target-agent Hello there" (valid format)
        When: Processing without registry
        Then: Attempts routing (fails with not found, not format error)

        Why: Valid format should proceed to routing, not be rejected.
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("@target-agent Hello there")
        )

        response_lower = response.content.text.lower()
        assert "not found" in response_lower, (
            f"Expected routing attempt resulting in 'not found'. "
            f"Got: '{response.content.text}'. "
            f"Cause: Valid format rejected or wrong error type. "
            f"Fix: Ensure format validation passes for @agent message"
        )
        assert "invalid format" not in response_lower, (
            f"Valid format incorrectly rejected as invalid. "
            f"Got: '{response.content.text}'"
        )

    def test_mention_in_middle_of_text_not_treated_as_routing(
        self, bridge_without_registry, sample_text_message
    ):
        """
        Given: "Hello @target-agent there" (mention not at start)
        When: Processing the message
        Then: Treated as regular message (not A2A routing)

        Why: Only leading @mentions trigger A2A routing.
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("Hello @target-agent there")
        )

        response_lower = response.content.text.lower()
        # Should NOT try A2A routing - should be processed as normal message
        # Routing error would contain both "not found" and "agent" (e.g., "Agent not found")
        routing_triggered = "not found" in response_lower and "agent" in response_lower
        assert not routing_triggered, (
            f"Middle @mention incorrectly triggered routing. "
            f"Got: '{response.content.text}'. "
            f"Cause: Regex matches @mention anywhere. "
            f"Fix: Anchor regex to start of message"
        )

    @pytest.mark.parametrize("agent_id,expected_valid", [
        ("agent-123", True),      # Hyphen in ID
        ("agent_test", True),     # Underscore in ID
        ("agent.service", True),  # Dot in ID
        ("MyAgent", True),        # Mixed case
    ])
    def test_special_characters_in_agent_id(
        self, bridge_without_registry, sample_text_message, agent_id, expected_valid
    ):
        """
        Given: @mention with special characters in agent ID
        When: Processing the message
        Then: Parses agent ID correctly

        Why: Agent IDs may contain hyphens, underscores, dots.
        """
        response = bridge_without_registry.handle_message(
            sample_text_message(f"@{agent_id} Hello")
        )

        response_lower = response.content.text.lower()
        if expected_valid:
            # Should attempt routing, not reject format
            assert agent_id.lower() in response_lower or "not found" in response_lower, (
                f"Agent ID '{agent_id}' not parsed correctly. "
                f"Got: '{response.content.text}'. "
                f"Fix: Update agent ID regex to allow special chars"
            )


# =============================================================================
# Tests: Registry Lookup Behavior
# =============================================================================

class TestRegistryLookupBehavior:
    """Tests for agent lookup via registry HTTP endpoints."""

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_successful_lookup_calls_correct_endpoint(
        self, mock_get, bridge_with_registry, sample_text_message, mock_registry_response
    ):
        """
        Given: "@target-agent Hello" with registry configured
        When: Processing the message
        Then: Calls GET /lookup/target-agent on registry
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})

        bridge_with_registry.handle_message(sample_text_message("@target-agent Hello"))

        assert mock_get.called, (
            "Expected requests.get called for registry lookup. "
            "Cause: Registry lookup skipped. "
            "Fix: Ensure _lookup_agent() is invoked"
        )
        first_call_url = mock_get.call_args_list[0][0][0]
        assert "/lookup/target-agent" in first_call_url, (
            f"Expected /lookup/target-agent endpoint. "
            f"Got: '{first_call_url}'. "
            f"Fix: Check URL construction in _lookup_agent()"
        )

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_404_returns_not_found_message(
        self, mock_get, bridge_with_registry, sample_text_message, mock_registry_response
    ):
        """
        Given: Registry returns 404 for agent
        When: Looking up agent
        Then: Returns user-friendly "not found" message
        """
        mock_get.return_value = mock_registry_response(404, {"error": "Agent not found"})

        response = bridge_with_registry.handle_message(
            sample_text_message("@unknown-agent Hello")
        )

        assert "not found" in response.content.text.lower(), (
            f"Expected 'not found' for 404 response. "
            f"Got: '{response.content.text}'. "
            f"Cause: 404 status not handled. "
            f"Fix: Check status_code before parsing response"
        )

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_500_error_handled_gracefully(
        self, mock_get, bridge_with_registry, sample_text_message, mock_registry_response
    ):
        """
        Given: Registry returns 500 Internal Server Error
        When: Looking up agent
        Then: Returns error message (not crash)

        Why: Server errors should not crash the client.
        """
        mock_get.return_value = mock_registry_response(500, {"error": "Internal error"})

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "not found", "failed"], "registry 500 error")

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_timeout_handled_gracefully(
        self, mock_get, bridge_with_registry, sample_text_message
    ):
        """
        Given: Registry request times out
        When: Looking up agent
        Then: Returns error message (not crash)
        """
        mock_get.side_effect = Timeout("Connection timed out")

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "not found", "timeout"], "registry timeout")

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_connection_refused_handled_gracefully(
        self, mock_get, bridge_with_registry, sample_text_message
    ):
        """
        Given: Registry is unreachable (connection refused)
        When: Looking up agent
        Then: Returns error message (not crash)
        """
        mock_get.side_effect = ConnectionError("Connection refused")

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "not found"], "connection error")

    def test_no_registry_configured_returns_not_found(
        self, bridge_without_registry, sample_text_message
    ):
        """
        Given: Bridge has no registry_url configured
        When: Attempting to route @mention
        Then: Returns "not found" (cannot lookup)
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert "not found" in response.content.text.lower(), (
            f"Expected 'not found' when no registry configured. "
            f"Got: '{response.content.text}'. "
            f"Cause: Missing registry_url check. "
            f"Fix: Return early when registry_url is None"
        )

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_invalid_json_handled_gracefully(
        self, mock_get, bridge_with_registry, sample_text_message
    ):
        """
        Given: Registry returns invalid JSON
        When: Parsing response
        Then: Returns error (not crash)

        Why: Malformed registry responses should not crash client.
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "not found"], "invalid JSON response")

    @patch('nanda_core.core.agent_bridge.requests.get')
    def test_registry_missing_agent_url_field_handled(
        self, mock_get, bridge_with_registry, sample_text_message, mock_registry_response
    ):
        """
        Given: Registry returns JSON without agent_url field
        When: Parsing response
        Then: Returns not found (not KeyError crash)
        """
        mock_get.return_value = mock_registry_response(200, {"other_field": "value"})

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "not found"], "missing agent_url field")


# =============================================================================
# Tests: A2A Message Sending
# =============================================================================

class TestA2AMessageSending:
    """Tests for outbound A2A protocol communication."""

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_creates_a2a_client_with_target_url(
        self, mock_a2a_class, mock_get, bridge_with_registry,
        sample_text_message, mock_registry_response, mock_a2a_client
    ):
        """
        Given: Successful registry lookup returns target URL
        When: Sending message to agent
        Then: A2AClient is created with that URL
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})
        mock_a2a_class.return_value = mock_a2a_client("Response text")

        bridge_with_registry.handle_message(sample_text_message("@target-agent Hello"))

        mock_a2a_class.assert_called_once()
        call_str = str(mock_a2a_class.call_args)
        assert "http://target:6001" in call_str, (
            f"Expected A2AClient created with 'http://target:6001'. "
            f"Got: {call_str}. "
            f"Fix: Pass registry agent_url to A2AClient"
        )

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_includes_target_response_in_output(
        self, mock_a2a_class, mock_get, bridge_with_registry,
        sample_text_message, mock_registry_response, mock_a2a_client
    ):
        """
        Given: Target agent responds with text
        When: A2A communication succeeds
        Then: Response text appears in output message
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})
        mock_a2a_class.return_value = mock_a2a_client("Hello from target agent!")

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert "Hello from target agent" in response.content.text, (
            f"Expected target response in output. "
            f"Got: '{response.content.text}'. "
            f"Fix: Extract text from A2A response parts"
        )

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_a2a_send_failure_returns_error_message(
        self, mock_a2a_class, mock_get, bridge_with_registry,
        sample_text_message, mock_registry_response, mock_a2a_client
    ):
        """
        Given: Registry lookup succeeds but A2A send raises exception
        When: Processing message
        Then: Returns error message (not crash)
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})
        mock_a2a_class.return_value = mock_a2a_client(error=Exception("Connection failed"))

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert_error_response(response, ["error", "failed"], "A2A send failure")

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_empty_a2a_response_handled(
        self, mock_a2a_class, mock_get, bridge_with_registry,
        sample_text_message, mock_registry_response, mock_a2a_client
    ):
        """
        Given: Target agent returns response with no parts
        When: Processing response
        Then: Handles gracefully (not crash)

        Why: Some agents may return empty responses.
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})
        mock_a2a_class.return_value = mock_a2a_client(parts=[])  # Empty parts

        response = bridge_with_registry.handle_message(
            sample_text_message("@target-agent Hello")
        )

        assert isinstance(response, Message), (
            "Expected Message for empty A2A response. Got crash. "
            "Cause: Empty parts list not handled. "
            "Fix: Check parts list before accessing"
        )


# =============================================================================
# Tests: Incoming A2A Message Handling
# =============================================================================

class TestIncomingA2AMessageHandling:
    """Tests for handling messages received from other agents."""

    def test_parses_from_to_message_format(self, bridge_without_registry, sample_text_message):
        """
        Given: "FROM: sender\\nTO: test-agent\\nMESSAGE: content"
        When: Processing incoming message
        Then: Extracts sender and generates response
        """
        incoming = "FROM: sender-agent\nTO: test-agent\nMESSAGE: Hello from sender"
        response = bridge_without_registry.handle_message(sample_text_message(incoming))

        assert "sender-agent" in response.content.text, (
            f"Expected sender-agent mentioned in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: FROM field not parsed. "
            f"Fix: Parse FROM: line in incoming handler"
        )

    def test_reply_loop_prevention(self, bridge_without_registry, sample_text_message):
        """
        Given: Incoming message that is already a reply ("Response to...")
        When: Processing the message
        Then: Does NOT generate another reply (prevents infinite loop)

        Why: Without loop detection, agents would reply forever.
        """
        incoming_reply = (
            "FROM: other-agent\n"
            "TO: test-agent\n"
            "MESSAGE: Response to test-agent: Here's your answer"
        )
        response = bridge_without_registry.handle_message(sample_text_message(incoming_reply))

        # Should display the incoming reply
        assert "[other-agent]" in response.content.text, (
            f"Expected incoming reply displayed. "
            f"Got: '{response.content.text}'"
        )
        # Should NOT generate a new outbound reply
        assert not response.content.text.startswith("[test-agent] Response to other-agent"), (
            f"Loop prevention failed - generated reply to reply. "
            f"Got: '{response.content.text}'. "
            f"Fix: Check 'Response to' in MESSAGE content"
        )

    def test_missing_to_field_handled_gracefully(self, bridge_without_registry, sample_text_message):
        """
        Given: "FROM: sender\\nMESSAGE: Hello" (missing TO)
        When: Processing malformed incoming message
        Then: Returns response (not crash)
        """
        malformed = "FROM: sender-agent\nMESSAGE: Hello"
        response = bridge_without_registry.handle_message(sample_text_message(malformed))

        assert isinstance(response, Message), (
            "Expected Message for malformed incoming. Got crash. "
            "Fix: Validate required fields before parsing"
        )

    def test_empty_message_content_handled(self, bridge_without_registry, sample_text_message):
        """
        Given: "FROM: sender\\nTO: test-agent\\nMESSAGE: " (empty content)
        When: Processing
        Then: Returns response (not crash)
        """
        empty_content = "FROM: sender-agent\nTO: test-agent\nMESSAGE: "
        response = bridge_without_registry.handle_message(sample_text_message(empty_content))

        assert isinstance(response, Message), (
            "Expected Message for empty MESSAGE content. Got crash. "
            "Fix: Handle empty message body"
        )


# =============================================================================
# Tests: Message Metadata Preservation
# =============================================================================

class TestMessageMetadataPreservation:
    """Tests for conversation ID and metadata handling."""

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_preserves_conversation_id_through_a2a_flow(
        self, mock_a2a_class, mock_get, bridge_with_registry,
        mock_registry_response, mock_a2a_client
    ):
        """
        Given: Inbound message has conversation_id "conv-12345"
        When: Processing and returning response
        Then: Response preserves same conversation_id

        Why: Conversation tracking requires ID preservation.
        """
        mock_get.return_value = mock_registry_response(200, {"agent_url": "http://target:6001"})
        mock_a2a_class.return_value = mock_a2a_client("Response")

        msg = Message(
            content=TextContent(text="@target-agent Hello"),
            role=MessageRole.USER,
            conversation_id="conv-12345"
        )

        response = bridge_with_registry.handle_message(msg)

        assert response.conversation_id == "conv-12345", (
            f"Expected conversation_id 'conv-12345' preserved. "
            f"Got: '{response.conversation_id}'. "
            f"Fix: Copy conversation_id from input to output"
        )

    def test_generates_conversation_id_when_missing(self, bridge_without_registry, sample_text_message):
        """
        Given: Inbound message has no conversation_id
        When: Processing
        Then: Response has auto-generated conversation_id
        """
        msg = sample_text_message("Hello")
        msg.conversation_id = None

        response = bridge_without_registry.handle_message(msg)

        assert response.conversation_id is not None, (
            "Expected auto-generated conversation_id. Got None. "
            "Fix: Generate UUID when conversation_id missing"
        )
        assert len(response.conversation_id) > 8, (
            "Expected UUID-style conversation_id. "
            f"Got: '{response.conversation_id}'"
        )


# =============================================================================
# Tests: Edge Cases and Boundaries
# =============================================================================

class TestA2AEdgeCasesAndBoundaries:
    """Tests for boundary conditions and unusual inputs."""

    def test_very_long_message_handled(self, bridge_without_registry, sample_text_message):
        """
        Given: "@target-agent" followed by 10KB of text
        When: Processing
        Then: Handles without crash or truncation error
        """
        long_msg = "@target-agent " + "x" * 10000
        response = bridge_without_registry.handle_message(sample_text_message(long_msg))

        assert isinstance(response, Message), (
            "Expected Message for 10KB input. Got crash. "
            "Cause: Message length limit. "
            "Fix: Remove or increase limits"
        )

    @pytest.mark.parametrize("message,description", [
        ("@target-agent 你好", "Chinese characters"),
        ("@target-agent こんにちは", "Japanese characters"),
        ("@target-agent Привет", "Cyrillic characters"),
        ("@target-agent 안녕하세요", "Korean Hangul"),
        ("@target-agent مرحبا", "Arabic RTL script"),
        ("@target-agent שלום", "Hebrew RTL script"),
        ("@target-agent สวัสดี", "Thai script"),
        ("@target-agent नमस्ते", "Hindi Devanagari"),
        ("@target-agent Bonjour café", "French accents"),
        ("@target-agent Γεια σου", "Greek letters"),
        ("@target-agent Hello 🎉🤖", "Emoji"),
        ("@target-agent test،message", "Arabic comma punctuation"),
    ])
    def test_unicode_in_message_preserved(self, bridge_without_registry, sample_text_message, message, description):
        """
        Given: Message with unicode characters ({description})
        When: Processing
        Then: Unicode characters preserved (not crash)
        """
        response = bridge_without_registry.handle_message(
            sample_text_message(message)
        )

        assert isinstance(response, Message), (
            f"Expected Message for {description}. Got crash. "
            f"Cause: Unicode encoding error. "
            f"Fix: Ensure UTF-8 encoding throughout"
        )

    def test_self_mention_handled(self, bridge_without_registry, sample_text_message):
        """
        Given: "@test-agent Hello" (agent mentions itself)
        When: Processing
        Then: Handles gracefully (not infinite loop)

        Why: Self-routing could cause stack overflow without guard.
        """
        # Bridge is test-agent, mentioning @test-agent
        response = bridge_without_registry.handle_message(
            sample_text_message("@test-agent Hello to myself")
        )

        assert isinstance(response, Message), (
            "Expected Message for self-mention. Got crash/loop. "
            "Fix: Check for self-mention before routing"
        )

    def test_multiple_at_signs_in_message(self, bridge_without_registry, sample_text_message):
        """
        Given: "@agent1 Hello @agent2" (multiple @mentions)
        When: Processing
        Then: Routes to first agent only (predictable behavior)
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("@agent1 Hello @agent2")
        )

        response_lower = response.content.text.lower()
        # Should try to route to agent1 (first mention)
        assert "agent1" in response_lower or "not found" in response_lower, (
            f"Expected routing to first @mention. "
            f"Got: '{response.content.text}'"
        )

    def test_whitespace_around_agent_id_handled(self, bridge_without_registry, sample_text_message):
        """
        Given: "  @target-agent Hello" (leading whitespace)
        When: Processing
        Then: Handles appropriately
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("  @target-agent Hello")
        )

        # Leading whitespace may or may not trigger routing - just don't crash
        assert isinstance(response, Message), (
            "Expected Message for whitespace-prefixed input. Got crash."
        )

    def test_newline_in_message_body(self, bridge_without_registry, sample_text_message):
        """
        Given: "@target-agent Line1\\nLine2\\nLine3"
        When: Processing
        Then: Multiline message handled correctly
        """
        response = bridge_without_registry.handle_message(
            sample_text_message("@target-agent Line1\nLine2\nLine3")
        )

        assert isinstance(response, Message), (
            "Expected Message for multiline input. Got crash."
        )
