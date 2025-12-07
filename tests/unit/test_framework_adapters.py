"""
Unit tests for framework/LLM provider adapters.

Tests SimpleAgentBridge initialization, configuration, and validation.

SimpleAgentBridge is the main adapter that bridges LLM frameworks to A2A protocol:
- Required: agent_id, agent_logic
- Optional: registry_url, telemetry, mcp_registry_url, smithery_api_key

Tests That FAIL (expose library issues):

CLEAR BUGS (no parameter validation):
- test_agent_id_none_accepted_no_validation: agent_id=None creates broken bridge
- test_agent_logic_none_fails_at_use: agent_logic=None accepted, fails at use
- test_agent_logic_not_callable_fails_at_use: agent_logic="string" accepted, fails at use
- test_agent_logic_wrong_signature_fails_at_use: Wrong params accepted, fails at use

DEBATABLE (design decisions):
- test_empty_string_agent_id: Empty string allowed - should it be?
- test_whitespace_only_agent_id: Whitespace-only allowed - should it be?
"""

import pytest
from unittest.mock import Mock
from python_a2a import Message, MessageRole

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
# Tests: Import Verification
# =============================================================================

class TestImportVerification:
    """Verify that required imports work before running other tests."""

    def test_simple_agent_bridge_importable(self):
        """
        Given: NEST package installed
        When: Importing SimpleAgentBridge
        Then: Import succeeds without error
        """
        # This test verifies the import worked (pytestmark skipif handles failure)
        assert SimpleAgentBridge is not None, (
            "SimpleAgentBridge should be importable. "
            "Cause: Package not installed or dependency missing. "
            "Fix: Run 'pip install -e .[dev]' and 'pip install python-a2a==0.5.6'"
        )


# =============================================================================
# Tests: Parameter Validation - Bug Exposure
# =============================================================================

class TestParameterValidationBugs:
    """
    Tests exposing lack of parameter validation in SimpleAgentBridge.

    Library currently accepts invalid parameters at init time and fails
    gracefully at handle_message() time. These tests document this behavior.
    """

    def test_agent_id_none_accepted_no_validation(self, sample_text_message):
        """
        Given: agent_id=None (invalid)
        When: Creating bridge
        Then: Should raise TypeError at init

        CLEAR BUG: Library accepts None and creates broken bridge.
        Actual: Creates bridge with agent_id=None, logs show "Agent ID: None".
        """
        bridge = SimpleAgentBridge(agent_id=None, agent_logic=Mock(return_value="test"))

        # Bug: None is accepted without validation
        assert bridge.agent_id is not None, (
            f"agent_id=None was accepted without validation. "
            f"Got: agent_id={repr(bridge.agent_id)}. "
            f"Cause: No validation in __init__. "
            f"Fix: Add `if agent_id is None: raise TypeError('agent_id required')`"
        )

    def test_agent_logic_none_fails_at_use(self, sample_text_message):
        """
        Given: agent_logic=None (invalid)
        When: Creating bridge and calling handle_message
        Then: Should raise TypeError at init (fail fast)

        CLEAR BUG: Library accepts None at init, fails gracefully at use.
        Actual: Returns error message "[test] Error: 'NoneType' object is not callable"
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=None)
        response = bridge.handle_message(sample_text_message("hello"))

        # Bug: Error message returned instead of raising at init
        assert "NoneType" not in response.content.text, (
            f"agent_logic=None was accepted at init, failed at use. "
            f"Got: '{response.content.text}'. "
            f"Cause: No validation in __init__. "
            f"Fix: Add `if agent_logic is None: raise TypeError('agent_logic required')`"
        )

    def test_agent_logic_not_callable_fails_at_use(self, sample_text_message):
        """
        Given: agent_logic="not a function" (not callable)
        When: Creating bridge and calling handle_message
        Then: Should raise TypeError at init (fail fast)

        CLEAR BUG: Library accepts non-callable at init, fails gracefully at use.
        Actual: Returns error message "[test] Error: 'str' object is not callable"
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic="not a function")
        response = bridge.handle_message(sample_text_message("hello"))

        # Bug: Non-callable accepted, error at use time
        assert "not callable" not in response.content.text, (
            f"Non-callable agent_logic was accepted at init. "
            f"Got: '{response.content.text}'. "
            f"Cause: No callable check in __init__. "
            f"Fix: Add `if not callable(agent_logic): raise TypeError('agent_logic must be callable')`"
        )

    def test_agent_logic_wrong_signature_fails_at_use(self, sample_text_message):
        """
        Given: agent_logic with wrong signature (takes 0 params, needs 2)
        When: Creating bridge and calling handle_message
        Then: Should validate signature at init or provide clear error

        DEBATABLE: Library catches error gracefully but doesn't validate at init.
        Actual: Returns "[test] Error: func() takes 0 positional arguments but 2 were given"
        """
        def bad_logic():  # Takes 0 params, should take 2 (message, conversation_id)
            return "test"

        bridge = SimpleAgentBridge(agent_id="test", agent_logic=bad_logic)
        response = bridge.handle_message(sample_text_message("hello"))

        # The error is graceful but could be validated at init
        assert "positional arguments" not in response.content.text, (
            f"Wrong signature accepted at init, failed at use. "
            f"Got: '{response.content.text}'. "
            f"Cause: No signature validation in __init__. "
            f"Fix: Check agent_logic accepts 2 params or use **kwargs"
        )


# =============================================================================
# Tests: Required Parameters
# =============================================================================

class TestRequiredParameters:
    """Tests for required parameter validation."""

    def test_init_requires_agent_id_and_agent_logic(self, mock_agent_logic):
        """
        Given: Required params (agent_id, agent_logic)
        When: Creating SimpleAgentBridge
        Then: Initializes successfully with both params stored
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        assert bridge.agent_id == "test-agent", (
            f"Expected agent_id='test-agent', got '{bridge.agent_id}'. "
            f"Cause: agent_id not stored in __init__. "
            f"Fix: Add self.agent_id = agent_id"
        )
        assert bridge.agent_logic == mock_agent_logic, (
            "agent_logic not stored correctly. "
            "Cause: agent_logic not assigned. "
            "Fix: Add self.agent_logic = agent_logic"
        )

    def test_agent_logic_is_callable(self, mock_agent_logic):
        """
        Given: A callable agent_logic function
        When: Calling agent_logic through bridge
        Then: Returns expected result without error
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic
        )

        result = bridge.agent_logic("test message", "conv-id")

        assert result is not None, (
            "agent_logic should return a result. "
            "Cause: Mock not configured correctly or agent_logic not callable. "
            "Fix: Verify agent_logic is a callable"
        )


# =============================================================================
# Tests: Optional Parameters (Consolidated)
# =============================================================================

class TestOptionalParameters:
    """Tests for optional parameter defaults and custom values."""

    def test_all_optional_params_default_to_none(self, mock_agent_logic):
        """
        Given: Only required params (agent_id, agent_logic)
        When: Creating bridge
        Then: All optional params default to None
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_agent_logic)

        assert bridge.registry_url is None, (
            f"registry_url should default to None. Got: {repr(bridge.registry_url)}"
        )
        assert bridge.mcp_registry_url is None, (
            f"mcp_registry_url should default to None. Got: {repr(bridge.mcp_registry_url)}"
        )
        assert bridge.smithery_api_key is None, (
            f"smithery_api_key should default to None. Got: {repr(bridge.smithery_api_key)}"
        )
        assert bridge.telemetry is None, (
            f"telemetry should default to None. Got: {repr(bridge.telemetry)}"
        )

    def test_all_optional_params_store_custom_values(self, mock_agent_logic, mock_telemetry):
        """
        Given: All optional params provided with custom values
        When: Creating bridge
        Then: All values stored correctly without modification
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com",
            mcp_registry_url="http://mcp.example.com",
            smithery_api_key="secret-key-123",
            telemetry=mock_telemetry
        )

        assert bridge.registry_url == "http://registry.example.com", (
            f"registry_url not stored. Got: {repr(bridge.registry_url)}"
        )
        assert bridge.mcp_registry_url == "http://mcp.example.com", (
            f"mcp_registry_url not stored. Got: {repr(bridge.mcp_registry_url)}"
        )
        assert bridge.smithery_api_key == "secret-key-123", (
            f"smithery_api_key not stored. Got: {repr(bridge.smithery_api_key)}"
        )
        assert bridge.telemetry == mock_telemetry, (
            f"telemetry not stored. Got: {repr(bridge.telemetry)}"
        )


# =============================================================================
# Tests: Full Configuration
# =============================================================================

class TestFullConfiguration:
    """Tests for bridge with all parameters configured."""

    def test_init_with_all_params(self, mock_agent_logic, mock_telemetry):
        """
        Given: All parameters provided
        When: Creating bridge
        Then: All parameters are correctly stored
        """
        bridge = SimpleAgentBridge(
            agent_id="full-config-agent",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com",
            telemetry=mock_telemetry,
            mcp_registry_url="http://mcp.example.com",
            smithery_api_key="api-key-xyz"
        )

        assert bridge.agent_id == "full-config-agent", "agent_id mismatch"
        assert bridge.registry_url == "http://registry.example.com", "registry_url mismatch"
        assert bridge.mcp_registry_url == "http://mcp.example.com", "mcp_registry_url mismatch"
        assert bridge.smithery_api_key == "api-key-xyz", "smithery_api_key mismatch"
        assert bridge.telemetry == mock_telemetry, "telemetry mismatch"

    def test_fully_configured_bridge_handles_message(self, mock_agent_logic, sample_text_message):
        """
        Given: Fully configured bridge
        When: Processing a message
        Then: Returns valid Message with AGENT role
        """
        bridge = SimpleAgentBridge(
            agent_id="functional-test",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com"
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        assert isinstance(response, Message), (
            f"Expected Message, got {type(response).__name__}. "
            f"Cause: handle_message not returning Message. "
            f"Fix: Check return type in handle_message()"
        )
        assert response.role == MessageRole.AGENT, (
            f"Expected AGENT role, got {response.role}. "
            f"Cause: Role assignment wrong. "
            f"Fix: Set role=MessageRole.AGENT in _create_response()"
        )


# =============================================================================
# Tests: Behavior Verification - Values Actually Used
# =============================================================================

class TestBehaviorVerification:
    """
    Tests that verify stored values are actually USED, not just stored.

    These tests go beyond storage verification to confirm the library
    actually uses the configured values during message processing.
    """

    def test_agent_logic_called_with_correct_params(self, sample_text_message):
        """
        Given: Bridge with agent_logic
        When: Processing regular message
        Then: agent_logic is called with (message_text, conversation_id)
        """
        mock_logic = Mock(return_value="response")
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_logic)

        bridge.handle_message(sample_text_message("Hello world"))

        # Verify agent_logic was called
        assert mock_logic.called, (
            "agent_logic was not called. "
            "Cause: Message didn't reach agent_logic. "
            "Fix: Check routing in handle_message()"
        )
        # Verify it received the message text
        call_args = mock_logic.call_args[0]
        assert "Hello world" in call_args[0], (
            f"agent_logic didn't receive message text. "
            f"Got args: {call_args}. "
            f"Fix: Pass message text to agent_logic"
        )

    def test_agent_logic_return_value_in_response(self, sample_text_message):
        """
        Given: agent_logic that returns specific text
        When: Processing message
        Then: Response contains agent_logic return value
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=Mock(return_value="Custom response from logic")
        )

        response = bridge.handle_message(sample_text_message("test"))

        assert "Custom response from logic" in response.content.text, (
            f"agent_logic return value not in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: Return value not used. "
            f"Fix: Include agent_logic result in response"
        )

    def test_agent_id_appears_in_response(self, mock_agent_logic, sample_text_message):
        """
        Given: Bridge with specific agent_id
        When: Processing message
        Then: Response references the agent_id (in prefix or elsewhere)
        """
        bridge = SimpleAgentBridge(agent_id="my-custom-agent", agent_logic=mock_agent_logic)

        response = bridge.handle_message(sample_text_message("test"))

        # agent_id should appear in response (as prefix or identification)
        assert "my-custom-agent" in response.content.text, (
            f"agent_id not in response. "
            f"Got: '{response.content.text}'. "
            f"Cause: agent_id not used in response formatting. "
            f"Fix: Include [agent_id] prefix in response"
        )

    def test_conversation_id_passed_to_agent_logic(self, sample_text_message):
        """
        Given: Message with conversation_id
        When: Processing message
        Then: conversation_id is passed to agent_logic
        """
        mock_logic = Mock(return_value="response")
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_logic)

        msg = sample_text_message("test")
        msg.conversation_id = "conv-12345"
        bridge.handle_message(msg)

        # Verify conversation_id was passed
        call_args = mock_logic.call_args[0]
        assert len(call_args) >= 2, (
            f"agent_logic should receive 2 args. "
            f"Got {len(call_args)} args. "
            f"Fix: Pass (message_text, conversation_id) to agent_logic"
        )
        assert call_args[1] == "conv-12345", (
            f"conversation_id not passed correctly. "
            f"Expected 'conv-12345', got '{call_args[1]}'. "
            f"Fix: Pass conversation_id as second arg"
        )


# =============================================================================
# Tests: Agent ID Format Variations
# =============================================================================

class TestAgentIdFormats:
    """Tests for different agent_id formats using parameterization."""

    @pytest.mark.parametrize("agent_id", [
        "simple",
        "with-hyphens",
        "with_underscores",
        "agent123",
        "UPPERCASE",
        "MixedCase",
        "data-analyst_v2.1",
    ])
    def test_agent_id_formats_preserved(self, mock_agent_logic, agent_id):
        """
        Given: Various agent_id formats (simple, hyphenated, underscored, numeric, mixed)
        When: Creating bridge
        Then: agent_id is stored exactly as provided (no sanitization)
        """
        bridge = SimpleAgentBridge(agent_id=agent_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == agent_id, (
            f"Expected '{agent_id}', got '{bridge.agent_id}'. "
            f"Cause: agent_id was modified/sanitized. "
            f"Fix: Store agent_id as-is without transformation"
        )


# =============================================================================
# Tests: URL Format Variations
# =============================================================================

class TestUrlFormats:
    """Tests for different URL formats."""

    @pytest.mark.parametrize("url,description", [
        ("http://localhost", "localhost without port"),
        ("http://localhost:8080", "localhost with port"),
        ("https://secure.example.com", "HTTPS URL"),
        ("http://example.com/api/v1", "URL with path"),
        ("http://example.com:9999/api/v1/registry", "URL with port and path"),
    ])
    def test_registry_url_formats_preserved(self, mock_agent_logic, url, description):
        """
        Given: Various URL formats (localhost, with port, HTTPS, with path)
        When: Creating bridge with registry_url
        Then: URL is stored exactly as provided
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url=url
        )

        assert bridge.registry_url == url, (
            f"URL not preserved for {description}. "
            f"Expected '{url}', got '{bridge.registry_url}'. "
            f"Cause: URL was modified. "
            f"Fix: Store registry_url as-is"
        )


# =============================================================================
# Tests: Edge Cases (Including DEBATABLE Design Decisions)
# =============================================================================

class TestEdgeCases:
    """
    Tests for edge cases and boundary conditions.

    Some tests document DEBATABLE design decisions where the library
    may be working as intended but the behavior could be improved.
    """

    def test_empty_string_agent_id(self, mock_agent_logic, sample_text_message):
        """
        Given: agent_id="" (empty string)
        When: Creating bridge and using it
        Then: Empty string is stored but causes issues

        DEBATABLE: Empty agent_id accepted - should it be?
        Counter-argument: Could be valid for anonymous agents.
        Problem: Breaks response format (shows "[] response" with empty prefix).
        """
        bridge = SimpleAgentBridge(agent_id="", agent_logic=mock_agent_logic)
        response = bridge.handle_message(sample_text_message("test"))

        # Documenting current behavior - empty string creates awkward output
        assert bridge.agent_id == "", (
            f"Empty string not preserved. Got: '{bridge.agent_id}'."
        )
        # The response will look like "[] mock response" - not ideal
        assert "[]" not in response.content.text or len(bridge.agent_id) > 0, (
            f"Empty agent_id creates awkward response format. "
            f"Got: '{response.content.text}'. "
            f"Cause: No validation for empty agent_id. "
            f"Fix: Add `if not agent_id.strip(): raise ValueError('agent_id cannot be empty')`"
        )

    def test_very_long_agent_id(self, mock_agent_logic):
        """
        Given: agent_id with 200 characters
        When: Creating bridge
        Then: Long agent_id is stored without truncation
        """
        long_id = "agent-" + "x" * 194  # 200 chars total
        bridge = SimpleAgentBridge(agent_id=long_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == long_id, (
            f"Expected 200-char agent_id, got {len(bridge.agent_id)} chars. "
            f"Cause: agent_id was truncated. "
            f"Fix: Remove length restriction on agent_id"
        )
        assert len(bridge.agent_id) == 200, (
            f"Expected 200 chars, got {len(bridge.agent_id)}. "
            f"Cause: Length truncation. "
            f"Fix: Store full agent_id"
        )

    def test_empty_string_registry_url(self, mock_agent_logic):
        """
        Given: registry_url="" (empty string)
        When: Creating bridge
        Then: Empty string is stored
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url=""
        )

        assert bridge.registry_url == "", (
            f"Expected empty string, got '{bridge.registry_url}'. "
            f"Cause: Empty string converted to None. "
            f"Fix: Don't convert empty string to None"
        )

    def test_whitespace_only_agent_id(self, mock_agent_logic, sample_text_message):
        """
        Given: agent_id="   " (whitespace only)
        When: Creating bridge and using it
        Then: Whitespace is stored but causes issues

        DEBATABLE: Whitespace-only agent_id accepted - should it be?
        Problem: Response shows "[   ] response" which is confusing.
        Counter-argument: Maybe there's a use case for invisible agents?
        """
        bridge = SimpleAgentBridge(agent_id="   ", agent_logic=mock_agent_logic)
        response = bridge.handle_message(sample_text_message("test"))

        # Documenting current behavior
        assert bridge.agent_id == "   ", (
            f"Whitespace not preserved. Got: '{bridge.agent_id}'."
        )
        # The response will look awkward with whitespace prefix
        assert "[   ]" not in response.content.text, (
            f"Whitespace-only agent_id creates confusing response. "
            f"Got: '{response.content.text}'. "
            f"Cause: No validation for whitespace-only agent_id. "
            f"Fix: Add `if not agent_id.strip(): raise ValueError(...)`"
        )

    @pytest.mark.parametrize("agent_id,description", [
        ("agent-中文", "Chinese characters"),
        ("agent-日本語", "Japanese characters"),
        ("agent-агент", "Cyrillic characters"),
        ("에이전트", "Korean Hangul"),
        ("وكيل", "Arabic RTL script"),
        ("סוכן", "Hebrew RTL script"),
        ("ตัวแทน", "Thai script"),
        ("एजेंट", "Hindi Devanagari"),
        ("café-agent", "French accents"),
        ("αβγ-agent", "Greek letters"),
        ("🤖-bot", "Emoji"),
        ("agent،test", "Arabic comma punctuation"),
    ])
    def test_unicode_in_agent_id(self, mock_agent_logic, agent_id, description):
        """
        Given: agent_id with unicode ({description})
        When: Creating bridge
        Then: Unicode is preserved
        """
        bridge = SimpleAgentBridge(agent_id=agent_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == agent_id, (
            f"Unicode not preserved for {description}. "
            f"Expected '{agent_id}', got '{bridge.agent_id}'. "
            f"Cause: Unicode not handled correctly. "
            f"Fix: Ensure UTF-8 support in agent_id storage"
        )

    def test_special_chars_in_smithery_api_key(self, mock_agent_logic):
        """
        Given: smithery_api_key with special characters
        When: Creating bridge
        Then: Special characters are preserved
        """
        special_key = "key_with-special.chars!@#$%"
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            smithery_api_key=special_key
        )

        assert bridge.smithery_api_key == special_key, (
            f"Expected '{special_key}', got '{bridge.smithery_api_key}'. "
            f"Cause: Special characters escaped or removed. "
            f"Fix: Store API key as-is without escaping"
        )
