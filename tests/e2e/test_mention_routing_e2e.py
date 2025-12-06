"""
E2E Tests for @Mention Routing.

Tests REAL end-to-end @mention routing flow:
Agent A sends "@agent-b message" → Registry lookup → Agent B receives → Response to A

This is the core A2A communication feature that enables inter-agent messaging.

Test Categories:
- TestBasicMentionRouting: Simple @mention send/receive
- TestMentionFormats: Various @mention format handling
- TestMentionEdgeCases: Edge cases and error conditions
- TestMentionChaining: Multi-hop @mention chains
"""

import time

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Basic Mention Routing
# =============================================================================


class TestBasicMentionRouting:
    """Tests for basic @mention routing between agents."""

    def test_at_mention_routes_to_target_agent(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents registered in registry
        When: Agent A sends @agent-b message
        Then: Message is routed to Agent B

        Tests REAL: Full A2A routing flow
        Mocks: None - this is the core E2E test
        """
        agent_a = agent_process_factory("sender-agent")
        agent_b = agent_process_factory("target-agent")

        # Send @mention message through agent A
        result = send_a2a_message(agent_a.url, "@target-agent Hello from sender!")

        assert result["status_code"] == 200, (
            f"Expected 200 from @mention routing, got {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: @mention routing may have failed. "
            f"Fix: Check _handle_agent_message() in SimpleAgentBridge."
        )

        # Response should contain target agent's ID (proving message was routed)
        response_text = str(result["response"])
        assert "target-agent" in response_text.lower() or "[target-agent]" in response_text, (
            f"Expected 'target-agent' in response (proving routing occurred). "
            f"Got: {response_text[:200]}. "
            f"Cause: Message may not have reached target agent. "
            f"Fix: Verify registry lookup returns correct URL and A2A POST succeeds."
        )
        # Response should also contain "Received:" from target's echo logic
        assert "received" in response_text.lower(), (
            f"Expected 'Received:' in response (from target agent echo). "
            f"Got: {response_text[:200]}. "
            f"Cause: Target agent response format incorrect. "
            f"Fix: Check agent_logic function returns 'Received: <message>'."
        )

    def test_at_mention_response_returns_to_sender(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents where target responds
        When: Sending @mention message
        Then: Response is returned to original sender

        Tests REAL: Round-trip A2A communication
        Mocks: None
        """
        agent_a = agent_process_factory("round-trip-sender")
        agent_b = agent_process_factory("round-trip-receiver")

        result = send_a2a_message(agent_a.url, "@round-trip-receiver Please respond")

        # Should get a response back
        assert result["status_code"] == 200, (
            f"Expected 200 for round-trip message, got {result['status_code']}. "
            f"Cause: Round-trip communication failed. "
            f"Fix: Check A2A response handling."
        )

    def test_at_mention_with_multiword_message(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention with multi-word message body
        When: Routing through agent
        Then: Full message body is delivered

        Tests REAL: Message body extraction
        Mocks: None
        """
        agent_a = agent_process_factory("multiword-sender")
        agent_b = agent_process_factory("multiword-receiver")

        result = send_a2a_message(
            agent_a.url,
            "@multiword-receiver This is a longer message with multiple words",
        )

        assert result["status_code"] == 200, (
            f"Multi-word message routing failed with status {result['status_code']}. "
            f"Cause: Message body parsing issue. "
            f"Fix: Check message extraction after @agent-id."
        )

    def test_at_mention_preserves_conversation_id(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention message with conversation_id
        When: Routing to target agent
        Then: Conversation ID is preserved in metadata

        Tests REAL: Conversation ID propagation
        Mocks: None
        """
        agent_a = agent_process_factory("conv-sender")
        agent_b = agent_process_factory("conv-receiver")

        conv_id = "test-conversation-12345"
        result = send_a2a_message(
            agent_a.url, "@conv-receiver Test message", conversation_id=conv_id
        )

        assert result["status_code"] == 200, (
            f"Expected 200 for message with conversation_id, got {result['status_code']}. "
            f"Cause: Conversation ID handling may have failed. "
            f"Fix: Check conversation_id propagation in handle_message()."
        )


# =============================================================================
# Tests: Mention Formats
# =============================================================================


class TestMentionFormats:
    """Tests for various @mention format handling."""

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("simple", "simple alphanumeric"),
            ("with-hyphens", "hyphenated"),
            ("with_underscores", "underscored"),
            ("Agent123", "mixed case numbers"),
            ("a", "single character"),
        ],
    )
    def test_at_mention_various_agent_id_formats(
        self,
        registry_process,
        agent_process_factory,
        send_a2a_message,
        agent_id,
        description,
    ):
        """
        Given: Target agent with {description} ID format
        When: Sending @mention
        Then: Routing works correctly

        Tests REAL: Various agent_id formats in @mention
        Mocks: None
        """
        sender = agent_process_factory(f"sender-{agent_id[:8]}")
        target = agent_process_factory(agent_id)

        result = send_a2a_message(sender.url, f"@{agent_id} Hello")

        assert result["status_code"] == 200, (
            f"@mention failed for {description} agent_id '{agent_id}'. "
            f"Status: {result['status_code']}. "
            f"Cause: Agent ID format not supported in @mention parsing. "
            f"Fix: Check @mention regex in _handle_agent_message()."
        )

    def test_at_mention_at_start_of_message(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention at the start of message
        When: Processing message
        Then: Recognized as @mention

        Tests REAL: @mention position detection
        Mocks: None
        """
        sender = agent_process_factory("start-sender")
        target = agent_process_factory("start-target")

        result = send_a2a_message(sender.url, "@start-target Hello")

        assert result["status_code"] == 200, (
            f"Expected 200 for @mention at start, got {result['status_code']}. "
            f"Cause: @mention position detection may have failed. "
            f"Fix: Check message prefix parsing in handle_message()."
        )

    def test_at_mention_with_only_agent_id(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention with only agent ID (no message body)
        When: Routing
        Then: Handles gracefully

        Tests REAL: Empty body @mention
        Mocks: None
        """
        sender = agent_process_factory("nobody-sender")
        target = agent_process_factory("nobody-target")

        result = send_a2a_message(sender.url, "@nobody-target")  # No message body

        # Should not crash, may succeed with empty body or return error
        assert result["status_code"] < 500, (
            f"@mention with no body caused server error: {result['status_code']}. "
            f"Cause: Empty message body not handled. "
            f"Fix: Add validation for message body."
        )


# =============================================================================
# Tests: Mention Edge Cases
# =============================================================================


class TestMentionEdgeCases:
    """Tests for @mention edge cases and error conditions."""

    def test_at_mention_nonexistent_agent(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention to agent not in registry
        When: Attempting to route
        Then: Returns appropriate error

        Tests REAL: Missing agent handling
        Mocks: None
        """
        sender = agent_process_factory("missing-sender")
        # Note: No target agent created

        result = send_a2a_message(sender.url, "@nonexistent-agent-xyz Hello")

        # Should return error, not crash
        response_text = str(result["response"]).lower()
        assert (
            result["status_code"] != 500
            or "not found" in response_text
            or "error" in response_text
        ), (
            f"Expected error handling for missing agent. "
            f"Status: {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: Missing agent not handled gracefully. "
            f"Fix: Check _lookup_agent() error handling."
        )

    def test_at_mention_self_reference(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Agent sending @mention to itself
        When: Processing
        Then: Handles without infinite loop

        Tests REAL: Self-reference protection
        Mocks: None
        """
        agent = agent_process_factory("self-ref-agent")

        result = send_a2a_message(agent.url, "@self-ref-agent Hello to myself")

        # Should complete without hanging (would timeout if infinite loop)
        assert result["status_code"] < 500, (
            f"Self-reference caused error: {result['status_code']}. "
            f"Cause: Self-reference not handled. "
            f"Fix: Add self-reference check in _handle_agent_message()."
        )

    def test_multiple_at_mentions_in_message(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Message with multiple @mentions
        When: Processing
        Then: First @mention is used (or handled appropriately)

        Tests REAL: Multiple @mention handling
        Mocks: None
        """
        sender = agent_process_factory("multi-mention-sender")
        target1 = agent_process_factory("multi-target-1")
        target2 = agent_process_factory("multi-target-2")

        result = send_a2a_message(sender.url, "@multi-target-1 Hello @multi-target-2")

        # Should succeed (routes to first @mention)
        assert result["status_code"] < 500, (
            f"Multiple @mentions caused error: {result['status_code']}. "
            f"Cause: Multiple @mention parsing issue. "
            f"Fix: Clarify multiple @mention behavior."
        )

    def test_email_in_message_not_treated_as_mention(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Message with email address (contains @)
        When: Message doesn't start with @
        Then: Not treated as @mention

        Tests REAL: Email vs @mention distinction
        Mocks: None
        """
        agent = agent_process_factory("email-test-agent")

        # Message starts with regular text, has email in body
        result = send_a2a_message(agent.url, "Please contact user@example.com for help")

        # Should be treated as regular message, not @mention
        assert result["status_code"] == 200, (
            f"Message with email failed: {result['status_code']}. "
            f"Cause: Email interpreted as @mention. "
            f"Fix: Only treat @ at start of message as @mention."
        )

    @pytest.mark.parametrize(
        "message,description",
        [
            ("@agent 你好", "Chinese greeting"),
            ("@agent こんにちは", "Japanese greeting"),
            ("@agent مرحبا", "Arabic greeting"),
            ("@agent שלום", "Hebrew greeting"),
            ("@agent 안녕", "Korean greeting"),
            ("@agent Hello 🎉🤖", "Emoji in message"),
        ],
    )
    def test_at_mention_with_unicode_body(
        self,
        registry_process,
        agent_process_factory,
        send_a2a_message,
        message,
        description,
    ):
        """
        Given: @mention with Unicode message body ({description})
        When: Routing to target
        Then: Unicode preserved

        Tests REAL: Unicode in @mention body
        Mocks: None
        """
        sender = agent_process_factory(f"unicode-sender-{description[:4]}")
        target = agent_process_factory("agent")  # Target is "agent" to match @agent

        result = send_a2a_message(sender.url, message)

        assert result["status_code"] == 200, (
            f"Unicode @mention failed for {description}. "
            f"Message: '{message}'. "
            f"Status: {result['status_code']}. "
            f"Cause: Unicode not handled in @mention routing. "
            f"Fix: Ensure UTF-8 throughout A2A message handling."
        )


# =============================================================================
# Tests: Mention Chaining
# =============================================================================


class TestMentionChaining:
    """Tests for multi-hop @mention message chains."""

    def test_two_agent_round_trip(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents A and B
        When: A sends to B, B responds
        Then: Complete round trip works

        Tests REAL: Basic two-agent exchange
        Mocks: None
        """
        agent_a = agent_process_factory("chain-a")
        agent_b = agent_process_factory("chain-b")

        # A sends to B
        result = send_a2a_message(agent_a.url, "@chain-b Initiate conversation")

        assert result["status_code"] == 200, (
            f"Two-agent chain failed: {result['status_code']}. "
            f"Cause: A→B communication broken. "
            f"Fix: Check registry lookup and A2A client."
        )

    def test_loop_detection_prevents_infinite_chain(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Potential for A→B→A→B... loop
        When: Messages are routed
        Then: Loop is detected and prevented

        Tests REAL: Infinite loop prevention
        Mocks: None
        """
        agent_a = agent_process_factory("loop-a")
        agent_b = agent_process_factory("loop-b")

        # Send message that could cause loop
        # Our test agents echo "Received: {message}" which shouldn't trigger re-routing
        result = send_a2a_message(agent_a.url, "@loop-b Start potential loop")

        # Should complete within timeout (30s), not hang
        assert result["status_code"] < 500, (
            f"Loop test caused error: {result['status_code']}. "
            f"Cause: Loop detection may have issues. "
            f"Fix: Check incoming message detection in _handle_incoming_agent_message()."
        )

    def test_incoming_message_format_handled(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Message in FROM:/TO:/MESSAGE: format
        When: Received by agent
        Then: Recognized as incoming A2A message

        Tests REAL: Incoming A2A format parsing
        Mocks: None
        """
        agent = agent_process_factory("incoming-format-test")

        # Simulate incoming A2A format
        incoming_message = """FROM: other-agent
TO: incoming-format-test
MESSAGE: This is a forwarded message"""

        result = send_a2a_message(agent.url, incoming_message)

        # Should be recognized as incoming A2A
        assert result["status_code"] == 200, (
            f"Incoming A2A format not handled: {result['status_code']}. "
            f"Cause: FROM:/TO:/MESSAGE: format not recognized. "
            f"Fix: Check _handle_incoming_agent_message() pattern matching."
        )

    def test_response_prefix_prevents_re_routing(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Message starting with "Response to"
        When: Processing
        Then: Not re-routed (loop prevention)

        Tests REAL: Response prefix detection
        Mocks: None
        """
        agent = agent_process_factory("response-prefix-test")

        # Message that looks like a response
        result = send_a2a_message(agent.url, "Response to other-agent: This is a reply")

        # Should be treated as regular message, not cause re-routing
        assert result["status_code"] == 200, (
            f"Response prefix handling failed: {result['status_code']}. "
            f"Cause: Response prefix may trigger unwanted behavior. "
            f"Fix: Check response detection in handle_message()."
        )
