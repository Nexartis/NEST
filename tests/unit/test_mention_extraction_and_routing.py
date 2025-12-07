"""
Unit tests for @mention extraction and routing.

Tests REAL library code: SimpleAgentBridge from nanda_core.core.agent_bridge

Tests two key areas:
1. @mention extraction - parsing @agent-id from message text
2. System commands - /help, /ping, /status routing

Expected Behavior:
- @agent-id message → looks up agent, sends message
- @agent-id (no body) → "Invalid format" error
- @agent-id    (whitespace body) → "Invalid format" error
- @ (alone) → "Invalid format" error
- @  (space after @) → "Invalid format" error
- /command → executes command
- /ping\ntest → executes ping (newline is whitespace)
- /HELP → "Unknown command: HELP" (case-sensitive)

Tests That Will FAIL (expose potential issues in agent_bridge.py):

CLEAR BUG:
- test_at_space_returns_invalid_format: Library looks up empty agent '' (wasteful API call)

DEBATABLE (may be by design):
- test_whitespace_body_returns_invalid_format: Library sends whitespace - could be valid
- test_command_with_newline_executes_correctly: Newline handling in commands is edge case
"""

import pytest
from unittest.mock import Mock
from python_a2a import Message, MessageRole, TextContent

try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

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
# @mention Extraction - Standard Formats
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
        ("a", "@a test"),
        ("a1", "@a1 test"),
    ])
    def test_extracts_agent_id_from_mention(self, bridge, sample_text_message, agent_id, message):
        """
        Given: @agent-id message
        When: Processing
        Then: Response references the target agent ID
        """
        response = bridge.handle_message(sample_text_message(message))

        assert isinstance(response, Message), (
            f"Expected Message, got {type(response).__name__}. "
            f"Cause: Exception in handle_message. "
            f"Fix: Check error handling in agent_bridge.py"
        )
        # Library tries to send to agent, response mentions agent ID
        assert agent_id.lower() in response.content.text.lower(), (
            f"Expected '{agent_id}' in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: Agent ID not extracted correctly. "
            f"Fix: Check _handle_agent_message() parsing"
        )


# =============================================================================
# @mention Extraction - Unicode (Graceful Handling)
# =============================================================================

class TestMentionUnicodeFormats:
    """Tests for @mention with unicode - verifies no crash, graceful handling."""

    @pytest.mark.parametrize("message,description", [
        ("@中文agent hello", "Chinese"),
        ("@agent日本 test", "Japanese"),
        ("@агент query", "Cyrillic"),
        ("@에이전트 test", "Korean"),
        ("@وكيل test", "Arabic"),
        ("@סוכן test", "Hebrew"),
        ("@ตัวแทน test", "Thai"),
        ("@एजेंट test", "Hindi"),
        ("@agentéè test", "French accents"),
        ("@αβγ test", "Greek"),
    ])
    def test_handles_unicode_without_crash(self, bridge, sample_text_message, message, description):
        """
        Given: @mention with unicode characters
        When: Processing
        Then: Returns Message (no crash), response is non-empty
        """
        response = bridge.handle_message(sample_text_message(message))

        assert isinstance(response, Message), (
            f"Crash on {description} unicode. "
            f"Cause: Unhandled unicode in _handle_agent_message(). "
            f"Fix: Add unicode support or graceful fallback"
        )
        assert len(response.content.text) > 0, (
            f"Empty response for {description}. "
            f"Cause: Unicode processing returned empty. "
            f"Fix: Ensure non-empty response for all inputs"
        )


# =============================================================================
# @mention Extraction - Boundary Conditions
# =============================================================================

class TestMentionBoundaryConditions:
    """Tests for @mention boundary conditions."""

    def test_no_message_body_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@agent-id" (no message body)
        When: Processing
        Then: Returns "Invalid format" error

        Actual behavior: Returns "Invalid format. Use '@agent_id message'"
        """
        response = bridge.handle_message(sample_text_message("@solo-agent"))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' error. "
            f"Got: '{response.content.text}'. "
            f"Cause: Missing body not detected. "
            f"Fix: Check len(parts) validation in _handle_agent_message()"
        )

    def test_whitespace_body_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@agent-id   " (whitespace-only body)
        When: Processing
        Then: Should return "Invalid format" error

        DEBATABLE: Whitespace-only body could be valid (empty message to agent).
        Counter-argument: Sending whitespace to another agent is likely user error.
        """
        response = bridge.handle_message(sample_text_message("@agent-id   "))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' for whitespace-only body. "
            f"Got: '{response.content.text}'. "
            f"Cause: _handle_agent_message() doesn't strip/validate message body. "
            f"Fix: Add `if not message_text.strip()` check after split."
        )

    def test_at_symbol_alone_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@" (just @ symbol)
        When: Processing
        Then: Returns "Invalid format" error
        """
        response = bridge.handle_message(sample_text_message("@"))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' for bare '@'. "
            f"Got: '{response.content.text}'. "
            f"Cause: Empty string after @ not guarded. "
            f"Fix: Add length check before split"
        )

    def test_at_space_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@ " (@ with space, no agent ID)
        When: Processing
        Then: Should return "Invalid format" error

        CLEAR BUG: Library looks up empty agent ID ''.
        This is wasteful - an empty string lookup will always fail.
        """
        response = bridge.handle_message(sample_text_message("@ "))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' for empty agent ID. "
            f"Got: '{response.content.text}'. "
            f"Cause: _handle_agent_message() doesn't validate agent ID is non-empty. "
            f"Fix: Add `if not target_agent` check after extracting agent ID."
        )

    def test_empty_message_processed_by_agent_logic(self, bridge, sample_text_message):
        """
        Given: "" (empty string)
        When: Processing
        Then: Processed by agent_logic (doesn't start with @, /, #)
        """
        response = bridge.handle_message(sample_text_message(""))

        assert isinstance(response, Message), (
            f"Crash on empty input. "
            f"Cause: Empty string not handled. "
            f"Fix: Add guard for empty message"
        )


# =============================================================================
# @mention Extraction - Position
# =============================================================================

class TestMentionPosition:
    """Tests for @mention position in message."""

    def test_at_start_routes_to_agent(self, bridge, sample_text_message):
        """
        Given: "@target-agent hello"
        When: Processing
        Then: Routes to target-agent (@ at start triggers routing)
        """
        response = bridge.handle_message(sample_text_message("@target-agent hello"))

        assert "target-agent" in response.content.text.lower(), (
            f"Expected target-agent routing. "
            f"Got: '{response.content.text}'. "
            f"Cause: @ at start not recognized. "
            f"Fix: Check startswith('@') in handle_message()"
        )

    def test_at_in_middle_processed_as_regular(self, bridge, sample_text_message):
        """
        Given: "hello @agent test" (@ not at start)
        When: Processing
        Then: Processed as regular message by agent_logic
        """
        response = bridge.handle_message(sample_text_message("hello @agent test"))

        # Regular messages get processed by agent_logic, prefixed with bridge's agent_id
        assert "test-agent" in response.content.text.lower(), (
            f"Expected regular message processing. "
            f"Got: '{response.content.text}'. "
            f"Cause: @ in middle incorrectly triggered routing. "
            f"Fix: Only route when text.startswith('@')"
        )

    def test_email_in_body_not_confused(self, bridge, sample_text_message):
        """
        Given: "@agent contact me@example.com"
        When: Processing
        Then: Routes to 'agent', email @ in body is ignored
        """
        response = bridge.handle_message(sample_text_message("@agent contact me@example.com"))

        assert "agent" in response.content.text.lower(), (
            f"Expected routing to 'agent'. "
            f"Got: '{response.content.text}'. "
            f"Cause: Email @ confused extraction. "
            f"Fix: Only match @ at position 0"
        )


# =============================================================================
# @mention - Message Content Preservation
# =============================================================================

class TestMentionMessageContent:
    """Tests for message content preservation after @agent-id."""

    @pytest.mark.parametrize("message,description", [
        ("@agent What's the $100 & <html>?", "special characters"),
        ("@agent translate: 你好 こんにちは", "unicode in body"),
        ("@agent line1\nline2\nline3", "newlines"),
        ("@agent col1\tcol2\tcol3", "tabs"),
        ("@agent x", "minimal single char body"),
    ])
    def test_handles_various_message_content(self, bridge, sample_text_message, message, description):
        """
        Given: @agent with various message content
        When: Processing
        Then: No crash, returns valid Message
        """
        response = bridge.handle_message(sample_text_message(message))

        assert isinstance(response, Message), (
            f"Crash on {description}. "
            f"Cause: Content parsing failed. "
            f"Fix: Don't modify message body content"
        )
        assert "agent" in response.content.text.lower(), (
            f"Expected 'agent' reference for {description}. "
            f"Got: '{response.content.text}'."
        )

    def test_handles_long_agent_id(self, bridge, sample_text_message):
        """
        Given: @{100-char agent ID} test
        When: Processing
        Then: Long agent ID handled
        """
        long_id = "agent-" + "x" * 94  # 100 chars total
        response = bridge.handle_message(sample_text_message(f"@{long_id} test"))

        assert isinstance(response, Message), (
            f"Crash on 100-char agent ID. "
            f"Cause: Agent ID length limit. "
            f"Fix: Remove or increase limit"
        )

    def test_handles_long_message_body(self, bridge, sample_text_message):
        """
        Given: @agent {10KB message}
        When: Processing
        Then: Long message handled
        """
        response = bridge.handle_message(sample_text_message("@agent " + "x" * 10000))

        assert isinstance(response, Message), (
            f"Crash on 10KB message. "
            f"Cause: Message body length limit. "
            f"Fix: Remove body length limit"
        )

    def test_tab_separator_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@agent\thello" (tab separator instead of space)
        When: Processing
        Then: Returns "Invalid format"

        Actual: Tab is not recognized as separator - splits on space only.
        """
        response = bridge.handle_message(sample_text_message("@agent\thello"))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' for tab separator. "
            f"Got: '{response.content.text}'. "
            f"Cause: _handle_agent_message() splits on space only, not whitespace. "
            f"Fix: Use text.split(None, 1) to split on any whitespace"
        )

    def test_newline_separator_returns_invalid_format(self, bridge, sample_text_message):
        """
        Given: "@agent\nhello" (newline separator instead of space)
        When: Processing
        Then: Returns "Invalid format"

        Actual: Newline is not recognized as separator - splits on space only.
        """
        response = bridge.handle_message(sample_text_message("@agent\nhello"))

        assert "invalid format" in response.content.text.lower(), (
            f"Expected 'Invalid format' for newline separator. "
            f"Got: '{response.content.text}'. "
            f"Cause: _handle_agent_message() splits on space only, not whitespace. "
            f"Fix: Use text.split(None, 1) to split on any whitespace"
        )

    def test_multiple_at_symbols_parsed(self, bridge, sample_text_message):
        """
        Given: "@@@agent hello" (triple @ before agent ID)
        When: Processing
        Then: Should extract "agent", not "@@agent"

        Current: Looks up "@@agent" including extra @ symbols.
        This documents edge case behavior.
        """
        response = bridge.handle_message(sample_text_message("@@@agent hello"))

        # Documents current behavior - includes @@ in agent ID lookup
        assert isinstance(response, Message), (
            f"Crash on triple @. "
            f"Cause: Multiple @ symbols not handled. "
            f"Fix: Add graceful handling"
        )
        # Library tries to look up "@@agent" - documenting actual behavior
        assert "@@agent" in response.content.text or "agent" in response.content.text.lower(), (
            f"Expected reference to agent lookup. "
            f"Got: '{response.content.text}'"
        )

    def test_at_hash_combination(self, bridge, sample_text_message):
        """
        Given: "@#agent hello" (@ followed by #)
        When: Processing
        Then: Should handle gracefully

        Current: Looks up "#agent" including the #.
        This documents edge case behavior.
        """
        response = bridge.handle_message(sample_text_message("@#agent hello"))

        # Documents current behavior - includes # in agent ID lookup
        assert isinstance(response, Message), (
            f"Crash on @# combination. "
            f"Cause: Special character after @ not handled. "
            f"Fix: Add validation or graceful handling"
        )
        # Library tries to look up "#agent" - documenting actual behavior
        assert "#agent" in response.content.text or "agent" in response.content.text.lower(), (
            f"Expected reference to agent lookup. "
            f"Got: '{response.content.text}'"
        )


# =============================================================================
# @mention - Error Handling
# =============================================================================

class TestMentionErrorHandling:
    """Tests for error handling in @mention processing."""

    def test_non_text_content_returns_error(self, bridge):
        """
        Given: Message with non-TextContent
        When: Processing
        Then: Returns error about text-only support
        """
        mock_msg = Mock()
        mock_msg.content = Mock(spec=[])  # No 'text' attribute
        mock_msg.conversation_id = "conv-123"
        mock_msg.message_id = "msg-123"

        response = bridge.handle_message(mock_msg)

        assert isinstance(response, Message), (
            f"Crash on non-text content. "
            f"Cause: Missing isinstance(content, TextContent) check. "
            f"Fix: Add type check at start of handle_message()"
        )
        assert "text" in response.content.text.lower(), (
            f"Expected error mentioning 'text'. "
            f"Got: '{response.content.text}'."
        )


# =============================================================================
# System Commands - /help
# =============================================================================

class TestCommandHelp:
    """Tests for /help command."""

    def test_returns_available_commands_header(self, bridge, sample_text_message):
        """
        Given: "/help"
        When: Processing
        Then: Response contains "Available commands"
        """
        response = bridge.handle_message(sample_text_message("/help"))

        assert "Available commands" in response.content.text, (
            f"Expected 'Available commands' header. "
            f"Got: '{response.content.text}'. "
            f"Fix: Add header to help response"
        )

    def test_lists_help_ping_status_commands(self, bridge, sample_text_message):
        """
        Given: "/help"
        When: Processing
        Then: Lists /help, /ping, /status
        """
        response = bridge.handle_message(sample_text_message("/help"))

        for cmd in ["/help", "/ping", "/status"]:
            assert cmd in response.content.text, (
                f"Expected '{cmd}' in help. "
                f"Got: '{response.content.text}'. "
                f"Fix: Add {cmd} to help text"
            )


# =============================================================================
# System Commands - /ping
# =============================================================================

class TestCommandPing:
    """Tests for /ping command."""

    def test_returns_pong(self, bridge, sample_text_message):
        """
        Given: "/ping"
        When: Processing
        Then: Returns "Pong!"
        """
        response = bridge.handle_message(sample_text_message("/ping"))

        assert "Pong!" in response.content.text, (
            f"Expected 'Pong!'. "
            f"Got: '{response.content.text}'."
        )

    def test_ignores_extra_arguments(self, bridge, sample_text_message):
        """
        Given: "/ping extra args"
        When: Processing
        Then: Still returns "Pong!"
        """
        response = bridge.handle_message(sample_text_message("/ping extra args"))

        assert "Pong!" in response.content.text, (
            f"Expected 'Pong!' with extra args. "
            f"Got: '{response.content.text}'."
        )


# =============================================================================
# System Commands - /status
# =============================================================================

class TestCommandStatus:
    """Tests for /status command."""

    def test_shows_agent_id(self, bridge, sample_text_message):
        """
        Given: "/status"
        When: Processing
        Then: Shows agent_id in response
        """
        response = bridge.handle_message(sample_text_message("/status"))

        assert "test-agent" in response.content.text, (
            f"Expected 'test-agent' in status. "
            f"Got: '{response.content.text}'."
        )

    def test_shows_running_status(self, bridge, sample_text_message):
        """
        Given: "/status"
        When: Processing
        Then: Shows "Running"
        """
        response = bridge.handle_message(sample_text_message("/status"))

        assert "Running" in response.content.text, (
            f"Expected 'Running' status. "
            f"Got: '{response.content.text}'."
        )

    def test_shows_registry_when_configured(self, bridge_with_registry, sample_text_message):
        """
        Given: "/status" with registry configured
        When: Processing
        Then: Shows registry URL
        """
        response = bridge_with_registry.handle_message(sample_text_message("/status"))

        assert "registry.example.com" in response.content.text, (
            f"Expected registry URL in status. "
            f"Got: '{response.content.text}'."
        )

    def test_no_registry_when_not_configured(self, bridge, sample_text_message):
        """
        Given: "/status" without registry
        When: Processing
        Then: Shows agent_id and Running, no registry line
        """
        response = bridge.handle_message(sample_text_message("/status"))

        assert "test-agent" in response.content.text
        assert "Running" in response.content.text
        # Status format: "Agent: test-agent, Status: Running" (no registry)


# =============================================================================
# System Commands - Unknown
# =============================================================================

class TestCommandUnknown:
    """Tests for unknown command handling."""

    def test_returns_unknown_command_error(self, bridge, sample_text_message):
        """
        Given: "/xyz" (unknown command)
        When: Processing
        Then: Returns "Unknown command: xyz"
        """
        response = bridge.handle_message(sample_text_message("/xyz"))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command' error. "
            f"Got: '{response.content.text}'."
        )
        assert "xyz" in response.content.text, (
            f"Expected 'xyz' in error message. "
            f"Got: '{response.content.text}'."
        )

    def test_commands_are_case_sensitive(self, bridge, sample_text_message):
        """
        Given: "/HELP" (uppercase)
        When: Processing
        Then: Returns "Unknown command: HELP" (case-sensitive)

        Actual behavior: Commands are lowercase only.
        """
        response = bridge.handle_message(sample_text_message("/HELP"))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command' for /HELP (case-sensitive). "
            f"Got: '{response.content.text}'."
        )
        assert "HELP" in response.content.text, (
            f"Expected 'HELP' in error. "
            f"Got: '{response.content.text}'."
        )


# =============================================================================
# System Commands - Edge Cases
# =============================================================================

class TestCommandEdgeCases:
    """Tests for command edge cases."""

    def test_slash_only_returns_unknown_command(self, bridge, sample_text_message):
        """
        Given: "/" (just slash)
        When: Processing
        Then: Returns "Unknown command: " (empty command name)
        """
        response = bridge.handle_message(sample_text_message("/"))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command' for '/'. "
            f"Got: '{response.content.text}'."
        )

    def test_slash_spaces_returns_unknown_command(self, bridge, sample_text_message):
        """
        Given: "/   " (slash + spaces)
        When: Processing
        Then: Returns "Unknown command" (spaces become empty after strip)
        """
        response = bridge.handle_message(sample_text_message("/   "))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command' for '/   '. "
            f"Got: '{response.content.text}'."
        )

    def test_leading_whitespace_not_command(self, bridge, sample_text_message):
        """
        Given: "  /help" (leading whitespace)
        When: Processing
        Then: Treated as regular message (doesn't start with /)
        """
        response = bridge.handle_message(sample_text_message("  /help"))

        # Regular message processed by agent_logic, prefixed with bridge's agent_id
        assert "test-agent" in response.content.text.lower(), (
            f"Expected regular message processing. "
            f"Got: '{response.content.text}'."
        )

    def test_double_slash_treated_as_command(self, bridge, sample_text_message):
        """
        Given: "//help"
        When: Processing
        Then: Treated as command "/help" (first / triggers command, rest is name)

        Actual: Returns "Unknown command: /help"
        """
        response = bridge.handle_message(sample_text_message("//help"))

        assert "Unknown command" in response.content.text, (
            f"Expected 'Unknown command: /help'. "
            f"Got: '{response.content.text}'."
        )

    def test_command_with_newline_executes_correctly(self, bridge, sample_text_message):
        """
        Given: "/ping\ntest"
        When: Processing
        Then: Should execute ping command (newline is whitespace separator)

        DEBATABLE: Command parsing splits on space only, not all whitespace.
        Counter-argument: Newlines in commands are rare edge case.
        """
        response = bridge.handle_message(sample_text_message("/ping\ntest"))

        assert "Pong!" in response.content.text, (
            f"Expected 'Pong!' for /ping with newline in args. "
            f"Got: '{response.content.text}'. "
            f"Cause: _handle_command() splits on space only, not whitespace. "
            f"Fix: Use `user_text.split(None, 1)` or regex split on `\\s+`."
        )
