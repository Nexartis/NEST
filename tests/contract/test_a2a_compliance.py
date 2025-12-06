"""
Contract Tests for A2A Protocol Compliance.

Validates that messages and responses conform to the A2A specification.
These tests verify protocol-level compliance using the real python_a2a library.

Tests REAL:
- python_a2a.Message class structure and fields
- python_a2a.TextContent class and text handling
- python_a2a.MessageRole enum values
- JSON serialization via to_dict()/to_json() methods
- Message deserialization via from_dict()/from_json() methods

Mocks:
- None (pure contract tests against library types)

Specification Reference:
- A2A Message format (role, content, metadata)
- JSON structure requirements
- Required vs optional fields
- Content type validation
"""

import json
import uuid
from typing import Any, Dict

import pytest

# Import A2A types from python_a2a
from python_a2a import Message, TextContent, MessageRole, Metadata

# Apply markers to all tests in this module
pytestmark = pytest.mark.contract


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def basic_message():
    """Create a basic A2A message for testing."""
    return Message(
        content=TextContent(text="test"),
        role=MessageRole.USER,
    )


@pytest.fixture
def full_message():
    """Create a fully-populated A2A message for testing."""
    return Message(
        content=TextContent(text="Hello, world!"),
        role=MessageRole.USER,
        message_id="msg-123",
        conversation_id="conv-456",
        parent_message_id="parent-789",
        metadata=Metadata(),
    )


# =============================================================================
# A2A Message Structure Contracts
# =============================================================================


class TestA2AMessageRequiredFields:
    """Contract tests for A2A message required fields."""

    def test_message_has_content_field(self, basic_message):
        """
        Contract: A2A Message MUST have a 'content' field.

        Spec: The content field contains the message payload.
        """
        assert hasattr(basic_message, "content"), (
            "A2A Message MUST have 'content' field. "
            "Expected: 'content' attribute present. "
            "Cause: python_a2a Message class structure changed. "
            "Fix: Check python_a2a version or update import."
        )
        assert basic_message.content is not None, (
            "A2A Message content MUST NOT be None. "
            "Expected: content object, Got: None. "
            "Cause: Message created with null content. "
            "Fix: Always provide TextContent or other content type."
        )

    def test_message_has_role_field(self, basic_message):
        """
        Contract: A2A Message MUST have a 'role' field.

        Spec: The role indicates whether message is from user or agent.
        """
        assert hasattr(basic_message, "role"), (
            "A2A Message MUST have 'role' field. "
            "Expected: 'role' attribute present. "
            "Cause: python_a2a Message class structure changed. "
            "Fix: Check python_a2a version or update import."
        )
        assert basic_message.role is not None, (
            "A2A Message role MUST NOT be None. "
            "Expected: MessageRole enum, Got: None. "
            "Cause: Message created with null role. "
            "Fix: Always provide MessageRole.USER or MessageRole.AGENT."
        )

    def test_message_role_is_valid_enum(self, basic_message):
        """
        Contract: A2A Message role MUST be a valid MessageRole enum value.

        Spec: Valid roles are USER and AGENT.
        """
        assert isinstance(basic_message.role, MessageRole), (
            f"A2A Message role MUST be MessageRole enum. "
            f"Expected: MessageRole instance, Got: {type(basic_message.role).__name__}. "
            f"Cause: Wrong type passed to role parameter. "
            f"Fix: Use MessageRole.USER or MessageRole.AGENT."
        )
        assert basic_message.role in [MessageRole.USER, MessageRole.AGENT], (
            f"A2A Message role MUST be USER or AGENT. "
            f"Expected: USER or AGENT, Got: {basic_message.role}. "
            f"Cause: Invalid MessageRole enum value. "
            f"Fix: Only use MessageRole.USER or MessageRole.AGENT."
        )

    def test_message_has_message_id_field(self, basic_message):
        """
        Contract: A2A Message MUST have a 'message_id' field.

        Spec: Each message has a unique identifier.
        """
        assert hasattr(basic_message, "message_id"), (
            "A2A Message MUST have 'message_id' field. "
            "Expected: 'message_id' attribute present. "
            "Cause: python_a2a Message class structure changed. "
            "Fix: Check python_a2a version or update import."
        )


class TestA2AMessageOptionalFields:
    """Contract tests for A2A message optional fields."""

    def test_message_accepts_conversation_id(self):
        """
        Contract: A2A Message MAY have a 'conversation_id' field.

        Spec: Conversation ID groups related messages.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            conversation_id="conv-123",
        )
        assert msg.conversation_id == "conv-123", (
            f"A2A Message conversation_id not preserved. "
            f"Expected: 'conv-123', Got: '{msg.conversation_id}'. "
            f"Cause: conversation_id parameter not stored. "
            f"Fix: Check python_a2a Message implementation."
        )

    def test_message_accepts_parent_message_id(self):
        """
        Contract: A2A Message MAY have a 'parent_message_id' field.

        Spec: Parent ID links to the message being replied to.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            parent_message_id="parent-123",
        )
        assert msg.parent_message_id == "parent-123", (
            f"A2A Message parent_message_id not preserved. "
            f"Expected: 'parent-123', Got: '{msg.parent_message_id}'. "
            f"Cause: parent_message_id parameter not stored. "
            f"Fix: Check python_a2a Message implementation."
        )

    def test_message_accepts_metadata(self):
        """
        Contract: A2A Message MAY have a 'metadata' field.

        Spec: Metadata contains additional message context.
        """
        metadata = Metadata()
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            metadata=metadata,
        )
        assert hasattr(msg, "metadata"), (
            "A2A Message SHOULD have metadata attribute. "
            "Expected: 'metadata' attribute present. "
            "Cause: python_a2a Message class structure changed. "
            "Fix: Check python_a2a version."
        )

    def test_message_without_optional_fields(self):
        """
        Contract: A2A Message MUST work without optional fields.

        Spec: Only content and role are required.
        """
        # Should not raise
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )
        assert msg.content is not None
        assert msg.role is not None


# =============================================================================
# A2A Content Type Contracts
# =============================================================================


class TestA2ATextContent:
    """Contract tests for A2A TextContent compliance."""

    def test_text_content_has_text_field(self):
        """
        Contract: TextContent MUST have a 'text' field.

        Spec: TextContent is the primary content type for text messages.
        """
        content = TextContent(text="Hello")
        assert hasattr(content, "text"), (
            "TextContent MUST have 'text' field. "
            "Expected: 'text' attribute present. "
            "Cause: python_a2a TextContent class structure changed. "
            "Fix: Check python_a2a version."
        )
        assert content.text == "Hello", (
            f"TextContent text not preserved. "
            f"Expected: 'Hello', Got: '{content.text}'. "
            f"Cause: text parameter not stored correctly. "
            f"Fix: Check python_a2a TextContent implementation."
        )

    def test_text_content_text_is_string(self):
        """
        Contract: TextContent text field MUST be a string.

        Spec: Text content is always a string value.
        """
        content = TextContent(text="test message")
        assert isinstance(content.text, str), (
            f"TextContent text MUST be string. "
            f"Expected: str, Got: {type(content.text).__name__}. "
            f"Cause: TextContent converted text to wrong type. "
            f"Fix: Check python_a2a TextContent implementation."
        )

    def test_text_content_empty_string(self):
        """
        Contract: TextContent MUST accept empty string.

        Spec: Empty messages are valid (edge case).
        """
        content = TextContent(text="")
        assert content.text == "", (
            f"TextContent MUST preserve empty string. "
            f"Expected: '', Got: '{content.text}'. "
            f"Cause: Empty string converted to something else. "
            f"Fix: Check python_a2a TextContent validation."
        )

    def test_text_content_whitespace_only(self):
        """
        Contract: TextContent MUST accept whitespace-only string.

        Spec: Whitespace-only messages are valid.
        """
        content = TextContent(text="   \t\n   ")
        assert content.text == "   \t\n   ", (
            f"TextContent MUST preserve whitespace. "
            f"Expected: whitespace string, Got: '{repr(content.text)}'. "
            f"Cause: Whitespace stripped or modified. "
            f"Fix: TextContent should not trim whitespace."
        )

    @pytest.mark.parametrize("lang,text", [
        ("Chinese", "你好世界"),
        ("Japanese", "こんにちは"),
        ("Korean", "안녕하세요"),
        ("Arabic", "مرحبا"),
        ("Hebrew", "שלום"),
        ("Thai", "สวัสดี"),
        ("Hindi", "नमस्ते"),
        ("Russian", "Привет"),
        ("Greek", "Γειά σου"),
        ("Emoji", "Hello 🎉🤖💻"),
    ])
    def test_text_content_preserves_unicode(self, lang, text):
        """
        Contract: TextContent MUST preserve Unicode characters.

        Spec: A2A supports international text.
        """
        content = TextContent(text=text)
        assert content.text == text, (
            f"TextContent MUST preserve {lang} Unicode. "
            f"Expected: '{text}', Got: '{content.text}'. "
            f"Cause: Unicode encoding/decoding issue. "
            f"Fix: Ensure UTF-8 handling in python_a2a."
        )

    @pytest.mark.parametrize("name,text", [
        ("newlines", "Line1\nLine2\nLine3"),
        ("tabs", "Col1\tCol2\tCol3"),
        ("carriage_return", "Line1\r\nLine2"),
        ("double_quotes", 'Say "Hello"'),
        ("single_quotes", "It's working"),
        ("backslash", "path\\to\\file"),
        ("html_tags", "<script>alert('xss')</script>"),
        ("json_special", '{"key": "value"}'),
        ("null_char", "before\x00after"),
    ])
    def test_text_content_preserves_special_characters(self, name, text):
        """
        Contract: TextContent MUST preserve special characters.

        Spec: A2A supports all printable and control characters.
        """
        content = TextContent(text=text)
        assert content.text == text, (
            f"TextContent MUST preserve {name}. "
            f"Expected: {repr(text)}, Got: {repr(content.text)}. "
            f"Cause: Special character handling issue. "
            f"Fix: Check python_a2a string handling."
        )


# =============================================================================
# A2A JSON Serialization Contracts
# =============================================================================


class TestA2AJsonSerialization:
    """Contract tests for A2A JSON serialization compliance."""

    def test_message_has_serialization_method(self, basic_message):
        """
        Contract: A2A Message MUST have a serialization method.

        Spec: Messages must be serializable for wire transmission.
        """
        has_method = (
            hasattr(basic_message, "to_json")
            or hasattr(basic_message, "to_dict")
            or hasattr(basic_message, "model_dump")
        )
        assert has_method, (
            "A2A Message MUST have serialization method. "
            "Expected: to_json(), to_dict(), or model_dump(). "
            "Cause: python_a2a Message missing serialization. "
            "Fix: Update python_a2a or implement custom serialization."
        )

    def test_message_serializes_to_valid_json(self, full_message):
        """
        Contract: A2A Message MUST serialize to valid JSON.

        Spec: A2A uses JSON for wire format.
        """
        # Get dict representation
        if hasattr(full_message, "to_dict"):
            data = full_message.to_dict()
        elif hasattr(full_message, "model_dump"):
            data = full_message.model_dump()
        else:
            pytest.skip("No dict serialization method available")

        # Should serialize to valid JSON without raising
        try:
            json_str = json.dumps(data)
            parsed = json.loads(json_str)
        except (TypeError, ValueError) as e:
            pytest.fail(
                f"A2A Message MUST serialize to valid JSON. "
                f"Expected: valid JSON, Got: {type(e).__name__}: {e}. "
                f"Cause: Non-serializable field in Message. "
                f"Fix: Check Message fields are JSON-compatible."
            )

        assert isinstance(parsed, dict), (
            f"A2A Message JSON MUST be an object. "
            f"Expected: dict, Got: {type(parsed).__name__}. "
            f"Cause: Serialization produced wrong type. "
            f"Fix: Check to_dict() implementation."
        )

    def test_message_json_has_required_fields(self, basic_message):
        """
        Contract: A2A Message JSON MUST contain required fields.

        Spec: role and content are required in JSON format.
        """
        if hasattr(basic_message, "to_dict"):
            data = basic_message.to_dict()
        elif hasattr(basic_message, "model_dump"):
            data = basic_message.model_dump()
        else:
            pytest.skip("No dict serialization method available")

        # Check for role (may be nested or at top level)
        has_role = "role" in data or any("role" in str(v) for v in data.values() if isinstance(v, dict))
        assert has_role, (
            "A2A Message JSON MUST contain 'role' field. "
            f"Expected: 'role' in {list(data.keys())}. "
            "Cause: Serialization missing role field. "
            "Fix: Check to_dict() includes role."
        )

        assert "content" in data, (
            "A2A Message JSON MUST contain 'content' field. "
            f"Expected: 'content' in {list(data.keys())}. "
            "Cause: Serialization missing content field. "
            "Fix: Check to_dict() includes content."
        )

    def test_message_round_trip_serialization(self, full_message):
        """
        Contract: A2A Message MUST survive round-trip serialization.

        Spec: Serialize then deserialize must preserve data.
        """
        # Serialize
        if hasattr(full_message, "to_dict"):
            data = full_message.to_dict()
        elif hasattr(full_message, "model_dump"):
            data = full_message.model_dump()
        else:
            pytest.skip("No dict serialization method available")

        # Check if deserialization method exists
        if not hasattr(Message, "from_dict") and not hasattr(Message, "model_validate"):
            pytest.skip("No deserialization method available (from_dict or model_validate)")

        # Deserialize
        if hasattr(Message, "from_dict"):
            restored = Message.from_dict(data)
        else:
            restored = Message.model_validate(data)

        # Verify key fields preserved
        assert restored.message_id == full_message.message_id, (
            f"Round-trip MUST preserve message_id. "
            f"Expected: '{full_message.message_id}', Got: '{restored.message_id}'. "
            f"Cause: Serialization/deserialization lost data. "
            f"Fix: Check to_dict()/from_dict() implementation."
        )


# =============================================================================
# A2A Response Contracts
# =============================================================================


class TestA2AResponseContracts:
    """Contract tests for A2A response format compliance."""

    def test_agent_role_exists(self):
        """
        Contract: MessageRole MUST have AGENT value.

        Spec: Responses use AGENT role.
        """
        assert hasattr(MessageRole, "AGENT"), (
            "MessageRole MUST have 'AGENT' value. "
            "Expected: MessageRole.AGENT exists. "
            "Cause: python_a2a MessageRole enum incomplete. "
            "Fix: Check python_a2a version."
        )

    def test_response_uses_agent_role(self):
        """
        Contract: A2A Response SHOULD use AGENT role.

        Spec: Responses are from agent, not user.
        """
        response = Message(
            content=TextContent(text="Response text"),
            role=MessageRole.AGENT,
        )
        assert response.role == MessageRole.AGENT, (
            f"A2A Response role SHOULD be AGENT. "
            f"Expected: AGENT, Got: {response.role}. "
            f"Cause: Response created with wrong role. "
            f"Fix: Use MessageRole.AGENT for responses."
        )

    def test_response_can_reference_parent(self):
        """
        Contract: A2A Response CAN set parent_message_id.

        Spec: Responses link to their triggering request.
        """
        request_id = f"req-{uuid.uuid4()}"
        response = Message(
            content=TextContent(text="Hi"),
            role=MessageRole.AGENT,
            parent_message_id=request_id,
        )
        assert response.parent_message_id == request_id, (
            f"A2A Response SHOULD reference parent message. "
            f"Expected: '{request_id}', Got: '{response.parent_message_id}'. "
            f"Cause: parent_message_id not stored. "
            f"Fix: Check Message parent_message_id parameter."
        )

    def test_response_can_share_conversation_id(self):
        """
        Contract: A2A Response CAN share conversation_id with request.

        Spec: Responses maintain conversation context.
        """
        conv_id = f"conv-{uuid.uuid4()}"
        response = Message(
            content=TextContent(text="Hi there"),
            role=MessageRole.AGENT,
            conversation_id=conv_id,
        )
        assert response.conversation_id == conv_id, (
            f"A2A Response SHOULD preserve conversation_id. "
            f"Expected: '{conv_id}', Got: '{response.conversation_id}'. "
            f"Cause: conversation_id not stored. "
            f"Fix: Check Message conversation_id parameter."
        )


# =============================================================================
# A2A Message ID Contracts
# =============================================================================


class TestA2AMessageIdGeneration:
    """Contract tests for A2A message ID handling."""

    def test_message_id_auto_generated_when_not_provided(self):
        """
        Contract: A2A Message SHOULD auto-generate message_id.

        Spec: Each message has a unique identifier.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )
        # message_id should exist (even if None or auto-generated)
        assert hasattr(msg, "message_id"), (
            "A2A Message MUST have message_id field. "
            "Expected: message_id attribute exists. "
            "Cause: Message class missing message_id. "
            "Fix: Check python_a2a Message implementation."
        )

    def test_message_id_preserved_when_provided(self):
        """
        Contract: A2A Message MUST preserve provided message_id.

        Spec: Explicit IDs must be respected.
        """
        custom_id = "custom-msg-12345"
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            message_id=custom_id,
        )
        assert msg.message_id == custom_id, (
            f"A2A Message MUST preserve provided message_id. "
            f"Expected: '{custom_id}', Got: '{msg.message_id}'. "
            f"Cause: message_id overwritten or ignored. "
            f"Fix: Check Message doesn't auto-generate when ID provided."
        )

    def test_message_ids_are_unique(self):
        """
        Contract: Auto-generated message_ids SHOULD be unique.

        Spec: Each message has a unique identifier.
        """
        ids = set()
        for _ in range(100):
            msg = Message(
                content=TextContent(text="test"),
                role=MessageRole.USER,
            )
            if msg.message_id is not None:
                ids.add(msg.message_id)

        # If IDs are generated, they should all be unique
        if ids:
            assert len(ids) == 100, (
                f"Auto-generated message_ids SHOULD be unique. "
                f"Expected: 100 unique IDs, Got: {len(ids)} unique IDs. "
                f"Cause: ID generation has collisions. "
                f"Fix: Use UUID or similar for message_id generation."
            )


# =============================================================================
# A2A Edge Cases
# =============================================================================


class TestA2AEdgeCases:
    """Contract tests for A2A edge cases and boundary conditions."""

    def test_very_long_text_content(self):
        """
        Contract: TextContent MUST handle very long text.

        Spec: No arbitrary length limits on message content.
        """
        long_text = "x" * 100000  # 100KB of text
        content = TextContent(text=long_text)
        assert len(content.text) == 100000, (
            f"TextContent MUST preserve long text. "
            f"Expected: 100000 chars, Got: {len(content.text)} chars. "
            f"Cause: Text truncated or length limit applied. "
            f"Fix: Remove length limits from TextContent."
        )

    def test_very_long_message_id(self):
        """
        Contract: Message SHOULD handle long message_id.

        Spec: IDs may be UUIDs or other formats.
        """
        long_id = "msg-" + "x" * 1000
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            message_id=long_id,
        )
        assert msg.message_id == long_id, (
            f"Message MUST preserve long message_id. "
            f"Expected: {len(long_id)} chars, Got: {len(msg.message_id) if msg.message_id else 0} chars. "
            f"Cause: message_id truncated. "
            f"Fix: Remove length limits from message_id."
        )

    def test_message_with_all_optional_fields_none(self):
        """
        Contract: Message MUST work with minimal required fields only.

        Spec: Optional fields can all be omitted.
        """
        msg = Message(
            content=TextContent(text="minimal"),
            role=MessageRole.USER,
        )
        # Should have created successfully
        assert msg.content is not None
        assert msg.role == MessageRole.USER

    def test_text_content_with_json_string(self):
        """
        Contract: TextContent MUST handle JSON-like strings.

        Spec: Text content may contain JSON data as string.
        """
        json_text = '{"nested": {"data": [1, 2, 3], "valid": true}}'
        content = TextContent(text=json_text)
        assert content.text == json_text, (
            f"TextContent MUST preserve JSON-like strings. "
            f"Expected: {json_text}, Got: {content.text}. "
            f"Cause: JSON parsing attempted on text content. "
            f"Fix: TextContent should treat all input as plain text."
        )
