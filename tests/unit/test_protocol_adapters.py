"""
Unit tests for A2A protocol adapters.

Tests message formatting and protocol compliance for SimpleAgentBridge.

Covers:
- A2A Message format (role, content, metadata)
- Conversation ID handling
- Parent message ID linking
- Error response formatting
- Edge cases (empty, special chars, unicode, long text)

WARNING (4 tests - xfail, type coercion):
- test_agent_logic_returns_none_handled: 'None' literal in response is confusing
- test_agent_logic_returns_int_handled: Int coerced to string silently
- test_agent_logic_returns_list_handled: List repr shown in response
- test_agent_logic_returns_dict_handled: Dict repr shown in response

Note: SLIM protocol tests will be added when SLIM support is implemented.
"""

import pytest
from unittest.mock import Mock
from python_a2a import MessageRole, TextContent, Message

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


@pytest.fixture
def bridge(mock_agent_logic):
    """Create a SimpleAgentBridge instance for testing."""
    return SimpleAgentBridge(agent_id="test-agent", agent_logic=mock_agent_logic)


class TestA2AMessageFormatting:
    """Tests for A2A message formatting compliance."""

    def test_response_has_agent_role(self, bridge, sample_text_message):
        """
        Given: A message from a user
        When: The bridge processes it
        Then: Response has role=MessageRole.AGENT
        """
        response = bridge.handle_message(sample_text_message("Hello"))

        assert response.role == MessageRole.AGENT, (
            f"Expected AGENT role, got {response.role}. "
            f"Cause: Role assignment changed in _create_response(). "
            f"Fix: Check _create_response() in agent_bridge.py"
        )

    def test_response_uses_text_content(self, bridge, sample_text_message):
        """
        Given: A processed message
        When: Response is created
        Then: Content is a TextContent instance
        """
        response = bridge.handle_message(sample_text_message("Test"))

        assert isinstance(response.content, TextContent), (
            f"Expected TextContent, got {type(response.content).__name__}. "
            f"Cause: Content wrapping changed or python_a2a version mismatch. "
            f"Fix: Check TextContent wrapping in _create_response()"
        )

    def test_response_includes_agent_id_prefix(self, mock_agent_logic, sample_text_message):
        """
        Given: An agent with ID "my-test-agent"
        When: Response is created
        Then: Response text starts with "[my-test-agent]"
        """
        agent_id = "my-test-agent"
        bridge = SimpleAgentBridge(agent_id=agent_id, agent_logic=mock_agent_logic)

        response = bridge.handle_message(sample_text_message("Hello"))

        expected_prefix = f"[{agent_id}]"
        assert response.content.text.startswith(expected_prefix), (
            f"Expected prefix '{expected_prefix}', got '{response.content.text[:50]}'. "
            f"Cause: Agent ID formatting changed. "
            f"Fix: Check text formatting in _create_response()"
        )

    def test_rejects_non_text_content(self, bridge):
        """
        Given: A message with non-TextContent
        When: Bridge processes it
        Then: Response indicates "Only text messages supported"
        """
        mock_msg = Mock()
        mock_msg.content = Mock()
        mock_msg.content.text = None
        mock_msg.conversation_id = "conv-123"
        mock_msg.message_id = "msg-123"

        response = bridge.handle_message(mock_msg)

        response_lower = response.content.text.lower()
        assert "only text" in response_lower or "text messages" in response_lower, (
            f"Expected 'Only text messages supported'. Got: '{response.content.text}'. "
            f"Cause: Non-TextContent validation message changed or missing. "
            f"Fix: Return 'Only text messages supported' in handle_message()"
        )


class TestA2AMessageMetadata:
    """Tests for A2A message metadata handling."""

    def test_preserves_conversation_id(self, bridge, sample_text_message):
        """
        Given: A message with conversation_id="conv-test-123"
        When: Processing the message
        Then: Response has the same conversation_id
        """
        conversation_id = "conv-test-123"
        msg = sample_text_message("Hello", conversation_id=conversation_id)

        response = bridge.handle_message(msg)

        assert response.conversation_id == conversation_id, (
            f"Expected '{conversation_id}', got '{response.conversation_id}'. "
            f"Cause: Conversation ID not passed to _create_response(). "
            f"Fix: Check handle_message() conversation_id handling"
        )

    def test_auto_generates_conversation_id(self, bridge, sample_text_message):
        """
        Given: A message without conversation_id
        When: Processing the message
        Then: Response has a generated conversation_id
        """
        msg = sample_text_message("Hello", conversation_id=None)

        response = bridge.handle_message(msg)

        assert response.conversation_id, (
            f"Expected auto-generated conversation ID, got None/empty. "
            f"Cause: UUID generation logic removed. "
            f"Fix: Check conversation_id assignment in handle_message()"
        )

    def test_links_parent_message_id(self, bridge, sample_text_message):
        """
        Given: A message with a specific message_id
        When: Creating a response
        Then: Response parent_message_id equals original message_id
        """
        msg = sample_text_message("Test")
        original_id = msg.message_id

        response = bridge.handle_message(msg)

        assert response.parent_message_id == original_id, (
            f"Expected parent_message_id='{original_id}', got '{response.parent_message_id}'. "
            f"Cause: parent_message_id not set in _create_response(). "
            f"Fix: Check _create_response() parent_message_id parameter"
        )

    def test_generates_unique_message_ids(self, bridge, sample_text_message):
        """
        Given: Two messages processed sequentially
        When: Creating responses
        Then: Each response has a different message_id
        """
        response1 = bridge.handle_message(sample_text_message("First"))
        response2 = bridge.handle_message(sample_text_message("Second"))

        assert response1.message_id != response2.message_id, (
            f"Both responses have same id='{response1.message_id}'. "
            f"Cause: Message ID not auto-generated. "
            f"Fix: Check Message() initialization in python_a2a"
        )
        assert response1.message_id, "Message ID cannot be None or empty"


class TestA2AErrorHandling:
    """Tests for error response formatting."""

    def test_catches_agent_logic_exception(self, sample_text_message):
        """
        Given: Agent logic that raises an exception
        When: Processing a message
        Then: Response contains error message (not stack trace)
        """
        failing_logic = Mock(side_effect=Exception("Database connection failed"))
        bridge = SimpleAgentBridge(agent_id="test-agent", agent_logic=failing_logic)

        response = bridge.handle_message(sample_text_message("Hello"))

        assert isinstance(response, Message), (
            f"Expected Message, got {type(response).__name__}. "
            f"Fix: Check exception handling in handle_message()"
        )
        assert "error" in response.content.text.lower(), (
            f"Expected error indication, got: '{response.content.text}'. "
            f"Fix: Check error formatting in handle_message()"
        )


class TestA2AEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_empty_response(self, sample_text_message):
        """
        Given: Agent logic returns empty string
        When: Creating the response
        Then: Response has agent ID prefix only
        """
        bridge = SimpleAgentBridge(agent_id="test-agent", agent_logic=Mock(return_value=""))

        response = bridge.handle_message(sample_text_message("Hello"))

        assert isinstance(response, Message), (
            f"Expected Message, got {type(response).__name__}. "
            f"Fix: Check empty string handling in _create_response()"
        )
        assert response.content.text.startswith("[test-agent]"), (
            f"Expected agent ID prefix, got: '{response.content.text}'. "
            f"Fix: Check text formatting in _create_response()"
        )

    def test_preserves_special_characters(self, sample_text_message):
        """
        Given: Agent returns text with special characters
        When: Creating the response
        Then: Special characters are preserved
        """
        special_text = "Hello! @user #tag $100 <xml> & \"quotes\" 'single'"
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=special_text)
        )

        response = bridge.handle_message(sample_text_message("Test"))

        assert special_text in response.content.text, (
            f"Expected '{special_text}' in response, got: '{response.content.text}'. "
            f"Cause: Text sanitization or encoding issue. "
            f"Fix: Check _create_response() for text transformation"
        )

    def test_preserves_unicode_characters(self, sample_text_message):
        """
        Given: Agent returns text with unicode characters
        When: Creating the response
        Then: Unicode characters are preserved
        """
        # Actual unicode characters
        unicode_text = "Chinese: \u4f60\u597d Japanese: \u3053\u3093\u306b\u3061\u306f Arabic: \u0645\u0631\u062d\u0628\u0627"
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=unicode_text)
        )

        response = bridge.handle_message(sample_text_message("Greet"))

        assert unicode_text in response.content.text, (
            f"Unicode not preserved. Expected: '{unicode_text}'. "
            f"Got: '{response.content.text}'. "
            f"Fix: Ensure UTF-8 handling in _create_response()"
        )

    def test_handles_long_response(self, sample_text_message):
        """
        Given: Agent returns 10KB of text
        When: Creating the response
        Then: Full text is preserved
        """
        long_text = "A" * 10000
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=long_text)
        )

        response = bridge.handle_message(sample_text_message("Generate"))

        assert len(response.content.text) >= 9900, (
            f"Expected 9900+ chars, got {len(response.content.text)}. "
            f"Cause: Text truncation. "
            f"Fix: Check for length limits in message creation"
        )

    def test_preserves_whitespace_formatting(self, sample_text_message):
        """
        Given: Agent returns multi-line formatted text
        When: Creating the response
        Then: Newlines and indentation are preserved
        """
        formatted_text = "Line 1\n  Indented line 2\n\nLine 4 after blank"
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=formatted_text)
        )

        response = bridge.handle_message(sample_text_message("Format"))

        assert "\n" in response.content.text, (
            f"Newlines not preserved. Got: '{response.content.text}'. "
            f"Fix: Check for text normalization"
        )
        assert "  Indented" in response.content.text, (
            f"Indentation not preserved. "
            f"Fix: Ensure no whitespace normalization"
        )


# =============================================================================
# BUG EXPOSURE TESTS - agent_logic return type validation
#
# CLEAR BUG: None produces confusing "None" string in response
# DEBATABLE: int/list/dict conversion - could be intentional flexibility
# =============================================================================

class TestAgentLogicReturnTypeValidation:
    """
    Tests for agent_logic return type handling.

    Library converts any return type to string via str().
    Whether this is a bug or intentional flexibility is debatable.
    """

    @pytest.mark.xfail(reason="WARNING: 'None' in response is confusing but technically works")
    def test_agent_logic_returns_none_handled(self, sample_text_message):
        """
        Expected: agent_logic returning None should return error or empty response.

        WARNING (not CRITICAL): Library shows literal "None" in response text.
        This is confusing to users - None should produce empty string.
        Severity: Low - UX issue, response is still returned.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=None)
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        # Should NOT contain literal "None" string
        assert "None" not in response.content.text, (
            f"Literal 'None' in response is confusing. "
            f"Got: '{response.content.text}'. "
            f"Cause: str(None) produces 'None'. "
            f"Fix: Add `if result is None: result = ''` in handle_message()"
        )

    @pytest.mark.xfail(reason="WARNING: Int coerced to string - may be intentional flexibility")
    def test_agent_logic_returns_int_handled(self, sample_text_message):
        """
        Expected: agent_logic returning int should return error or be rejected.

        WARNING (not CRITICAL): Library converts int to string via str().
        Could be intentional flexibility - some use cases return numbers.
        Severity: Low - type coercion is common pattern.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=42)
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        # Should either error or have type validation
        response_text = response.content.text
        assert "error" in response_text.lower() or "type" in response_text.lower(), (
            f"Expected error for non-string return type. "
            f"Got: '{response_text}'. "
            f"Cause: No type validation on agent_logic return value. "
            f"Fix: Add `if not isinstance(result, str): raise TypeError`"
        )

    @pytest.mark.xfail(reason="WARNING: List repr shown - ugly but technically works")
    def test_agent_logic_returns_list_handled(self, sample_text_message):
        """
        Expected: agent_logic returning list should return error or be rejected.

        WARNING (not CRITICAL): Library converts list to string repr via str().
        Shows "['item1', 'item2']" which is Python-specific and ugly.
        Severity: Low - UX issue, response is still returned.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value=["item1", "item2"])
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        # Should NOT contain Python list repr
        assert "['" not in response.content.text and "['item" not in response.content.text, (
            f"Python list repr in response is wrong. "
            f"Got: '{response.content.text}'. "
            f"Cause: str([...]) produces repr. "
            f"Fix: Validate agent_logic returns string type"
        )

    @pytest.mark.xfail(reason="WARNING: Dict repr shown - ugly but technically works")
    def test_agent_logic_returns_dict_handled(self, sample_text_message):
        """
        Expected: agent_logic returning dict should return error or be rejected.

        WARNING (not CRITICAL): Library converts dict to string repr via str().
        Shows "{'key': 'value'}" which is Python-specific and ugly.
        Severity: Low - UX issue, response is still returned.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=Mock(return_value={"key": "value"})
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        # Should NOT contain Python dict repr
        assert "{'" not in response.content.text and "{'key" not in response.content.text, (
            f"Python dict repr in response is wrong. "
            f"Got: '{response.content.text}'. "
            f"Cause: str({...}) produces repr. "
            f"Fix: Validate agent_logic returns string type"
        )
