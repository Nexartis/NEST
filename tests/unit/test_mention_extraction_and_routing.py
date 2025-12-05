"""
Unit tests for @mention extraction and routing.

Tests two key areas:
1. @mention extraction - parsing @agent-id from message text
2. System commands - /help, /ping, /status routing

The @mention pattern: @agent-id message
- Must start with @ symbol at beginning of message
- Agent ID: alphanumeric, hyphens, underscores, dots (implementation validates)
- Message body is required after agent ID
"""

import pytest
from unittest.mock import Mock
from python_a2a import Message, MessageRole, TextContent

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
def bridge_with_registry(mock_agent_logic):
    """Create a SimpleAgentBridge with registry URL configured."""
    return SimpleAgentBridge(
        agent_id="test-agent",
        agent_logic=mock_agent_logic,
        registry_url="http://registry.example.com"
    )


# =============================================================================
# Tests: @mention Extraction - Standard Formats
# =============================================================================

class TestMentionStandardFormats:
    """Tests for @agent-id extraction with standard ASCII formats."""

    @pytest.mark.parametrize("agent_id,message", [
        ("simple", "@simple hello"),
        ("with-hyphens", "@with-hyphens test"),
        ("with_underscores", "@with_underscores query"),
        ("agent123", "@agent123 test"),
        ("data-analyst_v2", "@data-analyst_v2 analyze"),
        ("agent.with.dots", "@agent.with.dots request"),
        ("UPPERCASE", "@UPPERCASE test"),
        ("MixedCase", "@MixedCase test"),
        ("123agent", "@123agent test"),
        ("a", "@a test"),  # Single character
        ("a1", "@a1 test"),  # Two characters
    ])
    def test_extracts_standard_agent_id(self, bridge, sample_text_message, agent_id, message):
        """
        Given: @mention with standard agent ID format
        When: Processing the message
        Then: Agent ID is extracted and referenced in response
        """
        response = bridge.handle_message(sample_text_message(message))

        assert isinstance(response, Message), (
            f"Expected Message response. Got: {type(response).__name__}. "
            f"Cause: handle_message raised exception. "
            f"Fix: Check exception handling in handle_message() at agent_bridge.py"
        )
        assert agent_id.lower() in response.content.text.lower(), (
            f"Expected '{agent_id}' in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: Agent ID '{agent_id}' not extracted by regex pattern. "
            f"Fix: Update AGENT_ID_PATTERN in _handle_agent_message()"
        )


# =============================================================================
# Tests: @mention Extraction - Unicode/International Characters
# =============================================================================

class TestMentionUnicodeFormats:
    """Tests for @mention with unicode characters - verifies graceful handling."""

    @pytest.mark.parametrize("message,description", [
        ("@\u4e2d\u6587agent hello", "Chinese characters in agent ID"),
        ("@agent\u65e5\u672c test", "Japanese characters in agent ID"),
        ("@\u0430\u0433\u0435\u043d\u0442 query", "Cyrillic characters in agent ID"),
        ("@agent\u00e9\u00e8 test", "French accents in agent ID"),
        ("@\u03b1\u03b2\u03b3 test", "Greek letters in agent ID"),
    ])
    def test_handles_unicode_agent_id_gracefully(self, bridge, sample_text_message, message, description):
        """
        Given: @mention with unicode characters in agent ID
        When: Processing the message
        Then: Returns valid Message (either processes or returns format error - no crash)
        """
        response = bridge.handle_message(sample_text_message(message))

        assert isinstance(response, Message), (
            f"Expected Message for {description}. "
            f"Got: {type(response).__name__} (crash or exception). "
            f"Cause: Unicode character caused unhandled exception. "
            f"Fix: Add unicode handling in _handle_agent_message() regex"
        )
        # Verify non-empty response
        assert response.content.text and len(response.content.text) > 0, (
            f"Expected non-empty response for {description}. "
            f"Got empty response. "
            f"Cause: Unicode processing returned empty string. "
            f"Fix: Ensure fallback response for unicode agent IDs"
        )


# =============================================================================
# Tests: @mention Extraction - Boundary Conditions
# =============================================================================

class TestMentionBoundaryConditions:
    """Tests for @mention boundary conditions - required format validation."""

    def test_returns_error_when_message_body_missing(self, bridge, sample_text_message):
        """
        Given: "@agent-id" with no message body
        When: Processing
        Then: Returns error indicating message body is required
        """
        response = bridge.handle_message(sample_text_message("@solo-agent"))

        assert isinstance(response, Message), (
            "Expected Message response. Got crash. "
            "Cause: No validation for missing message body. "
            "Fix: Add check for message body after agent ID extraction"
        )
        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'invalid format' error message. "
            f"Got: '{response.content.text}'. "
            f"Cause: Validation message not returned for bare @mention. "
            f"Fix: Return clear error in _handle_agent_message() when message body empty"
        )

    def test_returns_error_when_only_whitespace_after_id(self, bridge, sample_text_message):
        """
        Given: "@agent-id   " (whitespace only after agent ID)
        When: Processing
        Then: Returns error (whitespace-only is not a valid message body)
        """
        response = bridge.handle_message(sample_text_message("@agent-id   "))

        assert isinstance(response, Message), (
            "Expected Message response. Got crash. "
            "Cause: Whitespace-only message body not handled. "
            "Fix: Strip and validate message body is non-empty"
        )
        # Should indicate the agent or indicate invalid format
        response_lower = response.content.text.lower()
        assert "agent-id" in response_lower or "invalid" in response_lower, (
            f"Expected agent reference or format error. "
            f"Got: '{response.content.text}'. "
            f"Cause: Whitespace handling produced unexpected response. "
            f"Fix: Trim message body before processing in _handle_agent_message()"
        )

    def test_returns_error_when_at_symbol_alone(self, bridge, sample_text_message):
        """
        Given: "@" (just @ symbol)
        When: Processing
        Then: Returns error message, not crash
        """
        response = bridge.handle_message(sample_text_message("@"))

        assert isinstance(response, Message), (
            "Expected Message for '@' input. Got crash. "
            "Cause: Empty string after @ not guarded. "
            "Fix: Add len(text) > 1 check before extracting agent ID"
        )

    def test_returns_error_when_at_followed_by_space(self, bridge, sample_text_message):
        """
        Given: "@ " (@ with space, no agent ID)
        When: Processing
        Then: Returns error message, not crash
        """
        response = bridge.handle_message(sample_text_message("@ "))

        assert isinstance(response, Message), (
            "Expected Message for '@ ' input. Got crash. "
            "Cause: Space after @ not handled. "
            "Fix: Check agent ID is non-empty after stripping"
        )

    def test_returns_error_when_empty_message(self, bridge, sample_text_message):
        """
        Given: "" (empty string message)
        When: Processing
        Then: Returns valid response, not crash
        """
        response = bridge.handle_message(sample_text_message(""))

        assert isinstance(response, Message), (
            "Expected Message for empty input. Got crash. "
            "Cause: Empty string not handled. "
            "Fix: Add early return for empty message text"
        )


# =============================================================================
# Tests: @mention Extraction - Position Edge Cases
# =============================================================================

class TestMentionPositionEdgeCases:
    """Tests for @mention position in message - must be at start."""

    def test_at_start_extracts_agent_id(self, bridge, sample_text_message):
        """
        Given: "@agent hello world"
        When: Processing
        Then: Extracts "agent" from start position
        """
        response = bridge.handle_message(sample_text_message("@target-agent hello world"))

        assert "target-agent" in response.content.text.lower(), (
            f"Expected 'target-agent' in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: @ at start not recognized. "
            f"Fix: Ensure regex matches @ at position 0"
        )

    def test_not_at_start_treated_as_regular_message(self, bridge, sample_text_message):
        """
        Given: "hello @agent test" (@ not at start)
        When: Processing
        Then: Treats as regular message, not @mention routing
        """
        response = bridge.handle_message(sample_text_message("hello @agent test"))

        # Should be processed by agent_logic, not @mention handler
        assert isinstance(response, Message), (
            "Expected Message response. Got crash. "
            "Cause: @ in middle of text caused parsing error. "
            "Fix: Only match @ at start of message"
        )
        # Should NOT route to @agent, should process as regular message
        response_lower = response.content.text.lower()
        # Regular messages get processed by agent_logic and prefixed with agent ID
        assert "test-agent" in response_lower, (
            f"Expected regular message processing (agent ID prefix). "
            f"Got: '{response.content.text}'. "
            f"Cause: @ in middle incorrectly triggered @mention routing. "
            f"Fix: Check text.startswith('@') before @mention processing"
        )

    def test_email_in_message_not_confused_as_mention(self, bridge, sample_text_message):
        """
        Given: "@agent contact me@example.com"
        When: Processing
        Then: First @agent extracted, email @ ignored
        """
        response = bridge.handle_message(sample_text_message("@agent contact me@example.com"))

        assert "agent" in response.content.text.lower(), (
            f"Expected 'agent' extracted. "
            f"Got: '{response.content.text}'. "
            f"Cause: Email @ confused with @mention. "
            f"Fix: Only match first @ at message start"
        )


# =============================================================================
# Tests: @mention Message Content Edge Cases
# =============================================================================

class TestMentionMessageContent:
    """Tests for various message content after @agent-id."""

    def test_preserves_special_characters_in_message(self, bridge, sample_text_message):
        """
        Given: "@agent What's the $100 & <html> price?"
        When: Processing
        Then: Special characters in message body preserved
        """
        response = bridge.handle_message(
            sample_text_message("@agent What's the $100 & <html> price?")
        )

        assert isinstance(response, Message), (
            "Expected Message. Got crash. "
            "Cause: Special characters in message body caused error. "
            "Fix: Don't escape message body content"
        )

    def test_preserves_unicode_in_message(self, bridge, sample_text_message):
        """
        Given: "@agent translate: \u4f60\u597d \u3053\u3093\u306b\u3061\u306f"
        When: Processing
        Then: Unicode in message body preserved
        """
        response = bridge.handle_message(
            sample_text_message("@agent translate: \u4f60\u597d")
        )

        assert isinstance(response, Message), (
            "Expected Message for unicode message body. "
            "Cause: Unicode encoding error. "
            "Fix: Ensure UTF-8 throughout processing"
        )

    def test_preserves_newlines_in_message(self, bridge, sample_text_message):
        """
        Given: "@agent line1\nline2\nline3"
        When: Processing
        Then: Newlines preserved in message body
        """
        response = bridge.handle_message(
            sample_text_message("@agent line1\nline2\nline3")
        )

        assert isinstance(response, Message), (
            "Expected Message for multiline input. "
            "Cause: Newline caused parsing error. "
            "Fix: Don't split on newlines in message processing"
        )

    def test_preserves_tabs_in_message(self, bridge, sample_text_message):
        """
        Given: "@agent col1\tcol2\tcol3"
        When: Processing
        Then: Tab characters preserved
        """
        response = bridge.handle_message(
            sample_text_message("@agent col1\tcol2\tcol3")
        )

        assert isinstance(response, Message), (
            "Expected Message for tab-separated input. "
            "Cause: Tab character caused error. "
            "Fix: Don't strip or split on tabs"
        )

    def test_handles_very_long_agent_id(self, bridge, sample_text_message):
        """
        Given: @{100-char agent ID} test
        When: Processing
        Then: Long agent ID handled without truncation
        """
        long_id = "agent-" + "x" * 94  # 100 chars
        response = bridge.handle_message(sample_text_message(f"@{long_id} test"))

        assert isinstance(response, Message), (
            "Expected Message for 100-char agent ID. "
            "Cause: Agent ID length limit. "
            "Fix: Remove max length or increase limit"
        )

    def test_handles_very_long_message_body(self, bridge, sample_text_message):
        """
        Given: "@agent {10KB message}"
        When: Processing
        Then: Long message handled without truncation
        """
        response = bridge.handle_message(
            sample_text_message("@agent " + "x" * 10000)
        )

        assert isinstance(response, Message), (
            "Expected Message for 10KB input. "
            "Cause: Message body length limit. "
            "Fix: Remove max body length limit"
        )

    def test_handles_minimal_message_body(self, bridge, sample_text_message):
        """
        Given: "@agent x" (single char message body)
        When: Processing
        Then: Minimal message body accepted
        """
        response = bridge.handle_message(sample_text_message("@agent x"))

        assert isinstance(response, Message), (
            "Expected Message for single-char body. "
            "Cause: Minimum body length check too strict. "
            "Fix: Allow single character message body"
        )


# =============================================================================
# Tests: @mention Error Handling
# =============================================================================

class TestMentionErrorHandling:
    """Tests for error handling in @mention processing."""

    def test_returns_error_for_non_text_content(self, bridge):
        """
        Given: Message with content.text = None
        When: Processing
        Then: Returns error about text-only support
        """
        mock_msg = Mock()
        mock_msg.content = Mock()
        mock_msg.content.text = None
        mock_msg.conversation_id = "conv-123"
        mock_msg.message_id = "msg-123"

        response = bridge.handle_message(mock_msg)

        assert isinstance(response, Message), (
            "Expected Message for None text. Got crash. "
            "Cause: None content.text not validated. "
            "Fix: Check content.text is not None at start of handle_message()"
        )
        assert "text" in response.content.text.lower(), (
            f"Expected error mentioning 'text'. "
            f"Got: '{response.content.text}'. "
            f"Cause: Error message not descriptive. "
            f"Fix: Return 'Only text content supported' message"
        )


# =============================================================================
# Tests: System Commands - /help
# =============================================================================

class TestCommandHelp:
    """Tests for /help command."""

    def test_returns_command_list_with_header(self, bridge, sample_text_message):
        """
        Given: "/help"
        When: Processing
        Then: Response contains "Available commands" header
        """
        response = bridge.handle_message(sample_text_message("/help"))

        assert "Available commands" in response.content.text, (
            f"Expected 'Available commands' header. "
            f"Got: '{response.content.text}'. "
            f"Cause: Help header text changed. "
            f"Fix: Add 'Available commands:' to help response"
        )

    def test_lists_all_three_commands(self, bridge, sample_text_message):
        """
        Given: "/help"
        When: Processing
        Then: Response lists /help, /ping, /status
        """
        response = bridge.handle_message(sample_text_message("/help"))
        response_text = response.content.text

        for cmd in ["/help", "/ping", "/status"]:
            assert cmd in response_text, (
                f"Expected '{cmd}' in help text. "
                f"Got: '{response_text}'. "
                f"Cause: Command {cmd} missing from help. "
                f"Fix: Add {cmd} to command list in _handle_command()"
            )


# =============================================================================
# Tests: System Commands - /ping
# =============================================================================

class TestCommandPing:
    """Tests for /ping command."""

    def test_returns_pong(self, bridge, sample_text_message):
        """
        Given: "/ping"
        When: Processing
        Then: Response contains "Pong!"
        """
        response = bridge.handle_message(sample_text_message("/ping"))

        assert "Pong!" in response.content.text, (
            f"Expected 'Pong!' in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: Ping response changed. "
            f"Fix: Return 'Pong!' from ping case in _handle_command()"
        )

    def test_ignores_extra_arguments(self, bridge, sample_text_message):
        """
        Given: "/ping extra args here"
        When: Processing
        Then: Still returns "Pong!" (ignores extra args)
        """
        response = bridge.handle_message(sample_text_message("/ping extra args"))

        assert "Pong!" in response.content.text, (
            f"Expected 'Pong!' despite extra args. "
            f"Got: '{response.content.text}'. "
            f"Cause: Extra args broke command parsing. "
            f"Fix: Split on space and use only first token"
        )


# =============================================================================
# Tests: System Commands - /status
# =============================================================================

class TestCommandStatus:
    """Tests for /status command."""

    def test_shows_agent_id(self, bridge, sample_text_message):
        """
        Given: "/status"
        When: Processing
        Then: Response includes agent_id
        """
        response = bridge.handle_message(sample_text_message("/status"))

        assert "test-agent" in response.content.text, (
            f"Expected agent ID 'test-agent'. "
            f"Got: '{response.content.text}'. "
            f"Cause: Agent ID not in status. "
            f"Fix: Add self.agent_id to status response"
        )

    def test_shows_running_state(self, bridge, sample_text_message):
        """
        Given: "/status"
        When: Processing
        Then: Response indicates "Running" status
        """
        response = bridge.handle_message(sample_text_message("/status"))

        assert "Running" in response.content.text, (
            f"Expected 'Running' status. "
            f"Got: '{response.content.text}'. "
            f"Cause: Running indicator missing. "
            f"Fix: Add 'Status: Running' to response"
        )

    def test_shows_registry_url_when_configured(self, bridge_with_registry, sample_text_message):
        """
        Given: "/status" with registry_url="http://registry.example.com"
        When: Processing
        Then: Response includes registry URL
        """
        response = bridge_with_registry.handle_message(sample_text_message("/status"))

        assert "registry.example.com" in response.content.text, (
            f"Expected registry URL in status. "
            f"Got: '{response.content.text}'. "
            f"Cause: Registry URL not shown. "
            f"Fix: Add self.registry_url to status response"
        )

    def test_omits_registry_when_not_configured(self, bridge, sample_text_message):
        """
        Given: "/status" without registry_url
        When: Processing
        Then: Response omits registry (only shows agent ID and status)
        """
        response = bridge.handle_message(sample_text_message("/status"))

        # When no registry configured, status shows agent ID and Running without registry line
        assert "test-agent" in response.content.text, (
            f"Expected agent ID in status. "
            f"Got: '{response.content.text}'. "
            f"Cause: Agent ID missing from status. "
            f"Fix: Add self.agent_id to status response"
        )
        assert "Running" in response.content.text, (
            f"Expected 'Running' in status. "
            f"Got: '{response.content.text}'. "
            f"Cause: Status missing from response. "
            f"Fix: Add 'Running' to status response"
        )
        # Registry URL should not appear when not configured
        assert "registry" not in response.content.text.lower() or "none" not in response.content.text.lower(), (
            f"Registry should be omitted when not configured. "
            f"Got: '{response.content.text}'. "
            f"Implementation note: Status shows only agent+running when no registry"
        )


# =============================================================================
# Tests: System Commands - Unknown Commands
# =============================================================================

class TestCommandUnknown:
    """Tests for unknown command handling."""

    def test_returns_unknown_command_error(self, bridge, sample_text_message):
        """
        Given: "/xyz" (unknown command)
        When: Processing
        Then: Response contains "Unknown command"
        """
        response = bridge.handle_message(sample_text_message("/xyz"))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command' error. "
            f"Got: '{response.content.text}'. "
            f"Cause: No default case for unknown commands. "
            f"Fix: Add else clause in _handle_command()"
        )

    def test_uppercase_command_treated_as_unknown(self, bridge, sample_text_message):
        """
        Given: "/HELP" (uppercase)
        When: Processing
        Then: Returns "Unknown command" (commands are case-sensitive)
        """
        response = bridge.handle_message(sample_text_message("/HELP"))

        # Commands are lowercase-only, so /HELP should be unknown
        assert "Unknown command" in response.content.text or "Available commands" in response.content.text, (
            f"Expected either unknown error or help (if case-insensitive). "
            f"Got: '{response.content.text}'. "
            f"Cause: Case handling undefined. "
            f"Fix: Document case policy - either lowercase or accept both"
        )


# =============================================================================
# Tests: System Commands - Edge Cases
# =============================================================================

class TestCommandEdgeCases:
    """Tests for command edge cases."""

    def test_slash_only_returns_valid_response(self, bridge, sample_text_message):
        """
        Given: "/" (just slash)
        When: Processing
        Then: Returns Message, not crash
        """
        response = bridge.handle_message(sample_text_message("/"))

        assert isinstance(response, Message), (
            "Expected Message for '/'. Got crash. "
            "Cause: Empty command name not guarded. "
            "Fix: Check command name length > 0"
        )

    def test_slash_with_spaces_returns_valid_response(self, bridge, sample_text_message):
        """
        Given: "/   " (slash + spaces)
        When: Processing
        Then: Returns Message, not crash
        """
        response = bridge.handle_message(sample_text_message("/   "))

        assert isinstance(response, Message), (
            "Expected Message for '/   '. Got crash. "
            "Cause: Whitespace-only command not handled. "
            "Fix: Trim before checking command name"
        )

    def test_leading_whitespace_not_recognized_as_command(self, bridge, sample_text_message):
        """
        Given: "  /help" (leading whitespace)
        When: Processing
        Then: Treated as regular message, not command
        """
        response = bridge.handle_message(sample_text_message("  /help"))

        assert isinstance(response, Message), (
            "Expected Message. Got crash. "
            "Cause: Leading whitespace caused error. "
            "Fix: Check text.startswith('/') for commands"
        )

    def test_double_slash_returns_valid_response(self, bridge, sample_text_message):
        """
        Given: "//help"
        When: Processing
        Then: Returns Message (either unknown command or regular message)
        """
        response = bridge.handle_message(sample_text_message("//help"))

        assert isinstance(response, Message), (
            "Expected Message for '//help'. Got crash. "
            "Cause: Double slash not handled. "
            "Fix: Extract command name after first /"
        )

    def test_command_with_newline_in_args(self, bridge, sample_text_message):
        """
        Given: "/ping\ntest"
        When: Processing
        Then: Still executes ping (newline in args)
        """
        response = bridge.handle_message(sample_text_message("/ping\ntest"))

        assert isinstance(response, Message), (
            "Expected Message for command with newline. Got crash. "
            "Cause: Newline in command args not handled. "
            "Fix: Handle newlines in command argument parsing"
        )
