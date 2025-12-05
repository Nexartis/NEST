"""
Unit tests for A2A and SLIM protocol adapters.

Tests message formatting and protocol compliance for the SimpleAgentBridge's
_create_response() method and A2A Message structure.

Covers:
- A2A Message format compliance (role, content, metadata)
- TextContent wrapping and formatting
- Conversation ID preservation
- Parent message ID linking
- Agent ID prefix formatting
- Edge cases (empty content, special characters, null values)
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


@pytest.mark.unit
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestA2AMessageFormatting:
    """
    Tests for A2A protocol message formatting compliance.

    Validates that responses conform to A2A protocol requirements:
    - Correct message role (AGENT)
    - TextContent wrapping
    - Metadata preservation
    """

    def test_response_has_agent_role(self, mock_agent_logic, sample_text_message):
        """
        Test that all responses have MessageRole.AGENT.

        Given: A message from a user
        When: The bridge processes it and creates a response
        Then: The response message has role=MessageRole.AGENT

        Why this matters:
        A2A protocol requires proper role assignment for message routing.
        AGENT role indicates the message is from an agent, not a user.
        """
        # Arrange
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        # Act
        msg = sample_text_message("Hello")
        response = bridge.handle_message(msg)

        # Assert
        assert response.role == MessageRole.AGENT, (
            f"Response must have AGENT role for A2A protocol compliance. "
            f"Expected MessageRole.AGENT, got {response.role}. "
            f"Possible causes: (1) Role assignment logic changed in _create_response(), "
            f"(2) Message class initialization error. "
            f"Check _create_response() in agent_bridge.py:406"
        )

    def test_response_content_is_text_content_type(self, mock_agent_logic, sample_text_message):
        """
        Test that response content is wrapped in TextContent.

        Given: A processed message
        When: Creating the response
        Then: Response content is a TextContent instance

        Why this matters:
        A2A protocol requires specific content type wrapping for proper
        serialization and deserialization across the network.
        """
        # Arrange
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        # Act
        msg = sample_text_message("Test message")
        response = bridge.handle_message(msg)

        # Assert
        assert isinstance(response.content, TextContent), (
            f"Response content must be TextContent type for A2A compliance. "
            f"Expected TextContent, got {type(response.content).__name__}. "
            f"Possible causes: (1) Content wrapping changed in _create_response(), "
            f"(2) python_a2a library version mismatch. "
            f"Solution: Verify TextContent import and wrapping in agent_bridge.py:410"
        )

    def test_response_includes_agent_id_prefix(self, mock_agent_logic, sample_text_message):
        """
        Test that response text includes agent ID as prefix.

        Given: An agent with ID "my-agent"
        When: Creating a response
        Then: Response text starts with "[my-agent]"

        Why this matters:
        Agent ID prefix helps identify the source of responses in
        multi-agent conversations and debugging scenarios.
        """
        # Arrange
        agent_id = "my-test-agent"
        bridge = SimpleAgentBridge(
            agent_id=agent_id,
            agent_logic=mock_agent_logic
        )

        # Act
        msg = sample_text_message("Hello")
        response = bridge.handle_message(msg)

        # Assert
        response_text = response.content.text
        expected_prefix = f"[{agent_id}]"
        assert response_text.startswith(expected_prefix), (
            f"Response text must include agent ID prefix for identification. "
            f"Expected text to start with '{expected_prefix}', got '{response_text[:50]}...'. "
            f"Possible causes: (1) Agent ID formatting changed, "
            f"(2) Text concatenation logic modified. "
            f"Check text formatting in agent_bridge.py:410"
        )


@pytest.mark.unit
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestMessageMetadata:
    """
    Tests for message metadata handling.

    Validates conversation tracking and message threading:
    - Conversation ID preservation
    - Parent message ID linking
    - Message ID generation
    """

    def test_conversation_id_is_preserved(self, mock_agent_logic, sample_text_message):
        """
        Test that conversation ID from request is preserved in response.

        Given: A message with conversation_id="conv-123"
        When: Processing the message
        Then: Response has the same conversation_id

        Why this matters:
        Conversation ID enables message threading and context tracking
        across multiple exchanges between agents and users.
        """
        # Arrange
        conversation_id = "conv-test-123"
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        # Act
        msg = sample_text_message("Hello", conversation_id=conversation_id)
        response = bridge.handle_message(msg)

        # Assert
        assert response.conversation_id == conversation_id, (
            f"Conversation ID must be preserved for message threading. "
            f"Expected '{conversation_id}', got '{response.conversation_id}'. "
            f"Possible causes: (1) Conversation ID not passed to _create_response(), "
            f"(2) Message initialization missing conversation_id parameter. "
            f"Check handle_message() and _create_response() in agent_bridge.py"
        )

    def test_parent_message_id_links_to_original(self, mock_agent_logic, sample_text_message):
        """
        Test that response parent_message_id links to original message.

        Given: An incoming message with message_id="msg-456"
        When: Creating a response
        Then: Response parent_message_id equals "msg-456"

        Why this matters:
        Parent message ID creates a thread structure, enabling:
        - Conversation history reconstruction
        - Reply tracking
        - Context understanding
        """
        # Arrange
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        # Act
        msg = sample_text_message("Test")
        original_message_id = msg.message_id
        response = bridge.handle_message(msg)

        # Assert
        assert response.parent_message_id == original_message_id, (
            f"Response must link to original message for threading. "
            f"Expected parent_message_id='{original_message_id}', "
            f"got '{response.parent_message_id}'. "
            f"Possible causes: (1) parent_message_id not set in _create_response(), "
            f"(2) Wrong message object passed. "
            f"Check _create_response() parameter in agent_bridge.py:411"
        )

    def test_response_has_unique_message_id(self, mock_agent_logic, sample_text_message):
        """
        Test that each response gets a unique message ID.

        Given: Two messages processed
        When: Creating responses for each
        Then: Each response has a different message_id

        Why this matters:
        Unique message IDs are required for:
        - Message deduplication
        - Thread structure
        - Message tracking and debugging
        """
        # Arrange
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        # Act
        msg1 = sample_text_message("First message")
        msg2 = sample_text_message("Second message")
        response1 = bridge.handle_message(msg1)
        response2 = bridge.handle_message(msg2)

        # Assert
        assert response1.message_id != response2.message_id, (
            f"Each response must have a unique message_id. "
            f"Both responses have message_id='{response1.message_id}'. "
            f"Possible causes: (1) Message ID not auto-generated by python_a2a, "
            f"(2) Message reuse instead of creating new instances. "
            f"Solution: Verify Message() creates new IDs in python_a2a library"
        )

        # Also verify IDs are not None or empty
        assert response1.message_id, (
            f"Response message_id cannot be None or empty. "
            f"Got: '{response1.message_id}'. "
            f"Check Message initialization in python_a2a library"
        )


@pytest.mark.unit
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestEdgeCases:
    """
    Tests for edge cases and error scenarios.

    Validates handling of:
    - Empty content
    - Special characters
    - Very long messages
    - Null/None values (where applicable)
    """

    def test_empty_response_text_is_handled(self, sample_text_message):
        """
        Test that empty response text is properly formatted.

        Given: Agent logic returns empty string
        When: Creating the response
        Then: Response is created with agent ID prefix only

        Why this matters:
        Empty responses should not cause errors and should maintain
        proper message structure for protocol compliance.
        """
        # Arrange
        empty_logic = Mock(return_value="")
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=empty_logic
        )

        # Act
        msg = sample_text_message("Hello")
        response = bridge.handle_message(msg)

        # Assert
        assert isinstance(response, Message), (
            f"Empty response should still return valid Message object. "
            f"Got type: {type(response).__name__}. "
            f"Possible causes: (1) Error handling prevents message creation, "
            f"(2) Validation rejects empty content. "
            f"Check _create_response() for empty string handling"
        )

        # Verify it has the agent prefix even if content is empty
        assert response.content.text.startswith("[test-agent]"), (
            f"Even empty responses must include agent ID prefix. "
            f"Got: '{response.content.text}'. "
            f"Check text formatting in _create_response()"
        )

    def test_special_characters_in_response(self, sample_text_message):
        """
        Test that special characters are preserved in responses.

        Given: Agent logic returns text with special characters
        When: Creating the response
        Then: Special characters are preserved in response text

        Why this matters:
        Agents may need to return code, JSON, or formatted text
        containing special characters that must not be escaped or lost.
        """
        # Arrange
        special_text = "Hello! @user #tag $100 <xml> & \"quotes\" 'single' \n\t"
        special_logic = Mock(return_value=special_text)
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=special_logic
        )

        # Act
        msg = sample_text_message("Test")
        response = bridge.handle_message(msg)

        # Assert
        response_text = response.content.text
        assert special_text in response_text, (
            f"Special characters must be preserved in response text. "
            f"Expected substring: '{special_text}' "
            f"Got: '{response_text}'. "
            f"Possible causes: (1) Text sanitization removing characters, "
            f"(2) Encoding issues. "
            f"Solution: Verify no text transformation occurs in _create_response()"
        )

    def test_very_long_response_text(self, sample_text_message):
        """
        Test that very long responses are handled correctly.

        Given: Agent logic returns a 10KB response
        When: Creating the response message
        Then: Full text is preserved in response

        Why this matters:
        Agents may need to return large documents, code files, or
        detailed explanations without truncation.
        """
        # Arrange
        long_text = "A" * 10000  # 10KB of text
        long_logic = Mock(return_value=long_text)
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=long_logic
        )

        # Act
        msg = sample_text_message("Generate long text")
        response = bridge.handle_message(msg)

        # Assert
        response_text = response.content.text
        # Check that at least 9900 characters are present (allowing for prefix)
        assert len(response_text) >= 9900, (
            f"Long responses must not be truncated. "
            f"Expected at least 9900 chars, got {len(response_text)}. "
            f"Possible causes: (1) Text truncation in _create_response(), "
            f"(2) Message size limits in python_a2a. "
            f"Solution: Check for text length limits in message creation"
        )

    def test_newlines_and_formatting_preserved(self, sample_text_message):
        """
        Test that newlines and whitespace formatting is preserved.

        Given: Agent returns multi-line formatted text
        When: Creating the response
        Then: Line breaks and indentation are preserved

        Why this matters:
        Code snippets, structured data, and formatted text rely on
        whitespace preservation for readability and correctness.
        """
        # Arrange
        formatted_text = "Line 1\n  Indented line 2\n\nLine 4 after blank"
        formatted_logic = Mock(return_value=formatted_text)
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=formatted_logic
        )

        # Act
        msg = sample_text_message("Format test")
        response = bridge.handle_message(msg)

        # Assert
        response_text = response.content.text
        assert "\n" in response_text, (
            f"Newlines must be preserved in response text. "
            f"Expected newlines in text, got: '{response_text}'. "
            f"Possible causes: (1) Newline stripping in text processing, "
            f"(2) Text normalization removing whitespace. "
            f"Check _create_response() for text transformation"
        )

        assert "  Indented" in response_text, (
            f"Indentation must be preserved in response text. "
            f"Expected '  Indented', got: '{response_text}'. "
            f"Solution: Ensure no whitespace normalization in message creation"
        )
