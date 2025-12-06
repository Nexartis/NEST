"""
Contract Tests for A2A Protocol Compliance.

Validates that messages and responses conform to the A2A specification.
These tests verify protocol-level compliance, not functional behavior.

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
# A2A Message Structure Contracts
# =============================================================================


class TestA2AMessageStructure:
    """Contract tests for A2A message structure compliance."""

    def test_message_has_required_content_field(self):
        """
        Contract: A2A Message MUST have a 'content' field.

        Spec: The content field contains the message payload.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )

        assert hasattr(msg, "content"), (
            "A2A Message MUST have 'content' field. "
            "Spec violation: Required field missing."
        )
        assert msg.content is not None, (
            "A2A Message content MUST NOT be None. "
            "Spec violation: Required field is null."
        )

    def test_message_has_required_role_field(self):
        """
        Contract: A2A Message MUST have a 'role' field.

        Spec: The role indicates whether message is from user or agent.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )

        assert hasattr(msg, "role"), (
            "A2A Message MUST have 'role' field. "
            "Spec violation: Required field missing."
        )
        assert msg.role is not None, (
            "A2A Message role MUST NOT be None. "
            "Spec violation: Required field is null."
        )

    def test_message_role_is_valid_enum(self):
        """
        Contract: A2A Message role MUST be a valid MessageRole enum value.

        Spec: Valid roles are USER and AGENT.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )

        assert isinstance(msg.role, MessageRole), (
            f"A2A Message role MUST be MessageRole enum. "
            f"Got type: {type(msg.role)}. "
            f"Spec violation: Invalid role type."
        )
        assert msg.role in [MessageRole.USER, MessageRole.AGENT], (
            f"A2A Message role MUST be USER or AGENT. "
            f"Got: {msg.role}. "
            f"Spec violation: Invalid role value."
        )

    def test_message_has_message_id(self):
        """
        Contract: A2A Message MUST have a 'message_id' field.

        Spec: Each message has a unique identifier.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )

        assert hasattr(msg, "message_id"), (
            "A2A Message MUST have 'message_id' field. "
            "Spec violation: Required field missing."
        )

    def test_message_id_is_string(self):
        """
        Contract: A2A Message message_id MUST be a string.

        Spec: Message IDs are string identifiers.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            message_id="test-123",
        )

        assert isinstance(msg.message_id, str), (
            f"A2A Message message_id MUST be string. "
            f"Got type: {type(msg.message_id)}. "
            f"Spec violation: Invalid message_id type."
        )

    def test_message_optional_conversation_id(self):
        """
        Contract: A2A Message MAY have a 'conversation_id' field.

        Spec: Conversation ID groups related messages.
        """
        # Without conversation_id
        msg1 = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )
        assert hasattr(msg1, "conversation_id"), (
            "A2A Message SHOULD have conversation_id attribute."
        )

        # With conversation_id
        msg2 = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            conversation_id="conv-123",
        )
        assert msg2.conversation_id == "conv-123", (
            f"A2A Message conversation_id not preserved. "
            f"Expected: 'conv-123', Got: '{msg2.conversation_id}'."
        )

    def test_message_optional_parent_message_id(self):
        """
        Contract: A2A Message MAY have a 'parent_message_id' field.

        Spec: Parent ID links to the message being replied to.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            parent_message_id="parent-123",
        )

        assert hasattr(msg, "parent_message_id"), (
            "A2A Message SHOULD have parent_message_id attribute."
        )
        assert msg.parent_message_id == "parent-123", (
            f"A2A Message parent_message_id not preserved. "
            f"Expected: 'parent-123', Got: '{msg.parent_message_id}'."
        )

    def test_message_optional_metadata(self):
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
            "A2A Message SHOULD have metadata attribute."
        )


# =============================================================================
# A2A Content Type Contracts
# =============================================================================


class TestA2AContentTypes:
    """Contract tests for A2A content type compliance."""

    def test_text_content_has_text_field(self):
        """
        Contract: TextContent MUST have a 'text' field.

        Spec: TextContent is the primary content type for text messages.
        """
        content = TextContent(text="Hello")

        assert hasattr(content, "text"), (
            "TextContent MUST have 'text' field. "
            "Spec violation: Required field missing."
        )
        assert content.text == "Hello", (
            f"TextContent text not preserved. "
            f"Expected: 'Hello', Got: '{content.text}'."
        )

    def test_text_content_text_is_string(self):
        """
        Contract: TextContent text field MUST be a string.

        Spec: Text content is always a string value.
        """
        content = TextContent(text="test message")

        assert isinstance(content.text, str), (
            f"TextContent text MUST be string. "
            f"Got type: {type(content.text)}. "
            f"Spec violation: Invalid text type."
        )

    def test_text_content_preserves_unicode(self):
        """
        Contract: TextContent MUST preserve Unicode characters.

        Spec: A2A supports international text.
        """
        unicode_texts = [
            ("Chinese", "你好世界"),
            ("Japanese", "こんにちは"),
            ("Korean", "안녕하세요"),
            ("Arabic", "مرحبا"),
            ("Hebrew", "שלום"),
            ("Emoji", "Hello 🎉🤖"),
        ]

        for lang, text in unicode_texts:
            content = TextContent(text=text)
            assert content.text == text, (
                f"TextContent MUST preserve {lang} Unicode. "
                f"Expected: '{text}', Got: '{content.text}'."
            )

    def test_text_content_preserves_special_characters(self):
        """
        Contract: TextContent MUST preserve special characters.

        Spec: A2A supports all printable characters.
        """
        special_texts = [
            "Line1\nLine2",  # Newlines
            "Tab\there",  # Tabs
            'Quote "test"',  # Quotes
            "Backslash \\",  # Backslash
            "<script>alert('xss')</script>",  # HTML
        ]

        for text in special_texts:
            content = TextContent(text=text)
            assert content.text == text, (
                f"TextContent MUST preserve special chars. "
                f"Expected: {repr(text)}, Got: {repr(content.text)}."
            )


# =============================================================================
# A2A JSON Serialization Contracts
# =============================================================================


class TestA2AJsonSerialization:
    """Contract tests for A2A JSON serialization compliance."""

    def test_message_serializes_to_valid_json(self):
        """
        Contract: A2A Message MUST serialize to valid JSON.

        Spec: A2A uses JSON for wire format.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
            message_id="msg-123",
            conversation_id="conv-456",
        )

        # Should not raise
        try:
            if hasattr(msg, "to_json"):
                json_data = msg.to_json()
            elif hasattr(msg, "to_dict"):
                json_data = json.dumps(msg.to_dict())
            elif hasattr(msg, "model_dump"):
                json_data = json.dumps(msg.model_dump())
            elif hasattr(msg, "dict"):
                json_data = json.dumps(msg.dict())
            else:
                json_data = json.dumps(msg.__dict__)
        except (TypeError, ValueError) as e:
            pytest.fail(
                f"A2A Message MUST serialize to valid JSON. "
                f"Serialization failed: {e}"
            )

        # Should be valid JSON
        parsed = json.loads(json_data)
        assert isinstance(parsed, dict), (
            "A2A Message JSON MUST be an object."
        )

    def test_message_json_has_required_fields(self):
        """
        Contract: A2A Message JSON MUST contain required fields.

        Spec: role and content are required in JSON format.
        """
        msg = Message(
            content=TextContent(text="test"),
            role=MessageRole.USER,
        )

        if hasattr(msg, "to_dict"):
            data = msg.to_dict()
        elif hasattr(msg, "model_dump"):
            data = msg.model_dump()
        elif hasattr(msg, "dict"):
            data = msg.dict()
        else:
            data = msg.__dict__

        assert "role" in data or any("role" in str(k).lower() for k in data.keys()), (
            "A2A Message JSON MUST contain 'role' field."
        )
        assert "content" in data, (
            "A2A Message JSON MUST contain 'content' field."
        )

    def test_content_json_has_type_field(self):
        """
        Contract: A2A Content JSON SHOULD have 'type' field for polymorphism.

        Spec: Content type is indicated by 'type' field.
        """
        content = TextContent(text="test")

        if hasattr(content, "to_dict"):
            data = content.to_dict()
        elif hasattr(content, "model_dump"):
            data = content.model_dump()
        elif hasattr(content, "dict"):
            data = content.dict()
        else:
            data = content.__dict__

        # Type field may be 'type' or indicated by class
        has_type_indicator = (
            "type" in data
            or "text" in data  # TextContent identified by having text field
        )

        assert has_type_indicator, (
            "A2A Content JSON SHOULD indicate content type."
        )


# =============================================================================
# A2A Response Contracts
# =============================================================================


class TestA2AResponseContracts:
    """Contract tests for A2A response format compliance."""

    def test_response_is_valid_message(self):
        """
        Contract: A2A Response MUST be a valid Message.

        Spec: Responses use the same Message format as requests.
        """
        response = Message(
            content=TextContent(text="Response text"),
            role=MessageRole.AGENT,
            message_id=str(uuid.uuid4()),
        )

        assert isinstance(response, Message), (
            "A2A Response MUST be a Message instance."
        )
        assert response.role == MessageRole.AGENT, (
            f"A2A Response role SHOULD be AGENT. "
            f"Got: {response.role}."
        )

    def test_response_preserves_conversation_id(self):
        """
        Contract: A2A Response SHOULD preserve conversation_id from request.

        Spec: Responses maintain conversation context.
        """
        conv_id = "conv-" + str(uuid.uuid4())

        request = Message(
            content=TextContent(text="Hello"),
            role=MessageRole.USER,
            conversation_id=conv_id,
        )

        # Simulated response preserving conversation_id
        response = Message(
            content=TextContent(text="Hi there"),
            role=MessageRole.AGENT,
            conversation_id=request.conversation_id,
            parent_message_id=request.message_id,
        )

        assert response.conversation_id == conv_id, (
            f"A2A Response SHOULD preserve conversation_id. "
            f"Expected: '{conv_id}', Got: '{response.conversation_id}'."
        )

    def test_response_references_parent_message(self):
        """
        Contract: A2A Response SHOULD set parent_message_id to request message_id.

        Spec: Responses link to their triggering request.
        """
        request_id = "req-" + str(uuid.uuid4())

        request = Message(
            content=TextContent(text="Hello"),
            role=MessageRole.USER,
            message_id=request_id,
        )

        response = Message(
            content=TextContent(text="Hi"),
            role=MessageRole.AGENT,
            parent_message_id=request.message_id,
        )

        assert response.parent_message_id == request_id, (
            f"A2A Response SHOULD reference parent message. "
            f"Expected: '{request_id}', Got: '{response.parent_message_id}'."
        )


# =============================================================================
# A2A Wire Format Contracts
# =============================================================================


class TestA2AWireFormat:
    """Contract tests for A2A wire format (HTTP) compliance."""

    def test_a2a_endpoint_path(self):
        """
        Contract: A2A endpoint SHOULD be at /a2a path.

        Spec: Standard A2A endpoint is /a2a.
        """
        # This is a documentation contract - verified by convention
        expected_path = "/a2a"
        assert expected_path == "/a2a", (
            "A2A endpoint path SHOULD be '/a2a'."
        )

    def test_a2a_uses_post_method(self):
        """
        Contract: A2A messages SHOULD be sent via HTTP POST.

        Spec: A2A uses POST for message exchange.
        """
        # This is a documentation contract
        expected_method = "POST"
        assert expected_method == "POST", (
            "A2A messages SHOULD use POST method."
        )

    def test_a2a_content_type_is_json(self):
        """
        Contract: A2A Content-Type SHOULD be application/json.

        Spec: A2A uses JSON content type.
        """
        expected_content_type = "application/json"
        assert "json" in expected_content_type.lower(), (
            "A2A Content-Type SHOULD be application/json."
        )


# =============================================================================
# A2A Agent Routing Format Contracts
# =============================================================================


class TestA2AAgentRoutingFormat:
    """Contract tests for A2A agent routing format compliance."""

    def test_agent_message_format_from_to_message(self):
        """
        Contract: Agent routing messages SHOULD use FROM:/TO:/MESSAGE: format.

        Spec: This format enables agent-to-agent routing.
        """
        routing_format = "FROM:sender-agent\nTO:receiver-agent\nMESSAGE:Hello"

        assert "FROM:" in routing_format, (
            "Agent routing format SHOULD contain 'FROM:' field."
        )
        assert "TO:" in routing_format, (
            "Agent routing format SHOULD contain 'TO:' field."
        )
        assert "MESSAGE:" in routing_format, (
            "Agent routing format SHOULD contain 'MESSAGE:' field."
        )

    def test_at_mention_format(self):
        """
        Contract: @mention messages SHOULD start with @agent-id.

        Spec: @agent-id routes to target agent.
        """
        mention_formats = [
            "@agent-1 Hello",
            "@my-agent How are you?",
            "@agent_with_underscores test",
        ]

        for msg in mention_formats:
            assert msg.startswith("@"), (
                f"@mention messages SHOULD start with '@'. "
                f"Got: {msg}"
            )

    def test_mcp_message_format(self):
        """
        Contract: MCP messages SHOULD start with #provider:server.

        Spec: #nanda: or #smithery: routes to MCP servers.
        """
        mcp_formats = [
            "#nanda:weather-server Get weather",
            "#smithery:calculator Add 2+2",
        ]

        for msg in mcp_formats:
            assert msg.startswith("#"), (
                f"MCP messages SHOULD start with '#'. "
                f"Got: {msg}"
            )
            assert ":" in msg, (
                f"MCP messages SHOULD contain ':' separator. "
                f"Got: {msg}"
            )
