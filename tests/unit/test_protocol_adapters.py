"""
Unit tests for A2A and SLIM protocol adapters.

Tests message formatting and protocol compliance:
- Response role formatting (AGENT role)
- Conversation ID preservation
- Parent message ID tracking
"""

import pytest
from unittest.mock import Mock
from python_a2a import MessageRole

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
class TestResponseMessageFormatting:
    """Tests for response message formatting and protocol compliance."""

    def test_response_has_correct_role(self, mock_agent_logic, sample_text_message):
        """
        Response should have AGENT role.

        All responses from SimpleAgentBridge should have MessageRole.AGENT.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("Hello")
        response = bridge.handle_message(msg)

        assert response.role == MessageRole.AGENT, \
            f"Response role should be AGENT, got: {response.role}"

    def test_response_has_conversation_id(self, mock_agent_logic, sample_text_message):
        """
        Response should preserve conversation ID.

        Conversation ID from request should be carried to response.
        """
        conversation_id = "conv-456"

        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("Hello", conversation_id=conversation_id)
        response = bridge.handle_message(msg)

        assert response.conversation_id == conversation_id, \
            f"Conversation ID should be '{conversation_id}', got: {response.conversation_id}"

    def test_response_has_parent_message_id(self, mock_agent_logic, sample_text_message):
        """
        Response should reference parent message.

        parent_message_id should be set to the original message's ID.
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        msg = sample_text_message("Hello")
        response = bridge.handle_message(msg)

        assert response.parent_message_id == msg.message_id, \
            f"parent_message_id should be '{msg.message_id}', got: {response.parent_message_id}"
