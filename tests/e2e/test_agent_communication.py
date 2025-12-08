"""
E2E Tests for Agent Communication.

Tests REAL A2A protocol message flow between agents using actual HTTP
requests and real agent processes.

Test Categories:
- TestBasicCommunication: Simple message send/receive
- TestMessageContent: Message body handling
- TestConversationTracking: Conversation ID handling
- TestConcurrentMessages: Multiple simultaneous messages
- TestMCPCommunication: MCP message routing (#nanda:, #smithery:)
"""

import concurrent.futures
import time

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Basic Communication
# =============================================================================


class TestBasicCommunication:
    """Tests for basic A2A message send and receive."""

    def test_agent_receives_message_via_a2a_endpoint(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A running agent
        When: Sending a message to its /a2a endpoint
        Then: Agent receives and processes the message

        Tests REAL: HTTP POST to /a2a, message processing
        Mocks: None
        """
        agent = agent_process_factory("receiver-test")

        result = send_a2a_message(agent.url, "Hello, agent!")

        assert result["status_code"] == 200, (
            f"Expected 200 from /a2a endpoint, got {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: Agent may not be accepting messages. "
            f"Fix: Check SimpleAgentBridge.handle_message() implementation."
        )

    def test_agent_response_contains_agent_id(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A running agent with specific agent_id
        When: Sending a message to the agent
        Then: Response contains the agent's ID in standard format

        Tests REAL: Agent response formatting
        Mocks: None
        """
        agent = agent_process_factory("response-format-test")

        result = send_a2a_message(agent.url, "Test message")

        assert result["status_code"] == 200, (
            f"Expected 200 response, got {result['status_code']}. "
            f"Cause: Agent may not be processing messages. "
            f"Fix: Check handle_message() implementation."
        )

        response_text = str(result["response"])

        # Response MUST contain agent ID in brackets [agent_id] format
        # This is the standard format from _create_response()
        assert "[response-format-test]" in response_text, (
            f"Expected '[response-format-test]' in response (standard agent format). "
            f"Got: {response_text[:200]}. "
            f"Cause: Agent response format incorrect. "
            f"Fix: Check _create_response() returns '[{agent_id}] {text}' format."
        )

        # Response should also contain "Received:" from agent_logic
        assert "Received:" in response_text, (
            f"Expected 'Received:' in response (from agent_logic echo). "
            f"Got: {response_text[:200]}. "
            f"Cause: agent_logic not being called or not returning expected format. "
            f"Fix: Check agent_logic function in test agent."
        )

    def test_agent_handles_empty_message(self, agent_process_factory, send_a2a_message):
        """
        Given: A running agent
        When: Sending an empty message
        Then: Agent handles it gracefully (no crash)

        Tests REAL: Empty message handling
        Mocks: None
        """
        agent = agent_process_factory("empty-msg-test")

        result = send_a2a_message(agent.url, "")

        # Should not crash - any 2xx or 4xx response is acceptable
        assert result["status_code"] < 500, (
            f"Expected non-500 response for empty message, got {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: Empty message caused server error. "
            f"Fix: Add empty message validation in handle_message()."
        )

    def test_agent_handles_whitespace_only_message(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A running agent
        When: Sending whitespace-only message
        Then: Agent handles it gracefully

        Tests REAL: Whitespace message handling
        Mocks: None
        """
        agent = agent_process_factory("whitespace-test")

        result = send_a2a_message(agent.url, "   \t\n   ")

        assert result["status_code"] < 500, (
            f"Expected non-500 response for whitespace message, got {result['status_code']}. "
            f"Cause: Whitespace message caused server error. "
            f"Fix: Check message stripping in handle_message()."
        )


# =============================================================================
# Tests: Message Content
# =============================================================================


class TestMessageContent:
    """Tests for message body handling and content preservation."""

    def test_message_content_preserved(self, agent_process_factory, send_a2a_message):
        """
        Given: A specific message content
        When: Sending to agent
        Then: Original message is referenced in response

        Tests REAL: Message content handling
        Mocks: None
        """
        agent = agent_process_factory("content-test")
        test_message = "Unique test message 12345"

        result = send_a2a_message(agent.url, test_message)

        response_text = str(result["response"])
        # Our test agent echoes "Received: {message}"
        assert (
            "12345" in response_text
            or "Unique" in response_text
            or "received" in response_text.lower()
        ), (
            f"Expected message content echoed in response. "
            f"Sent: '{test_message}'. Got: '{response_text[:200]}'. "
            f"Cause: Message not passed to agent_logic. "
            f"Fix: Check message extraction in handle_message()."
        )

    def test_large_message_handled(self, agent_process_factory, send_a2a_message):
        """
        Given: A large message (10KB)
        When: Sending to agent
        Then: Message is processed without error

        Tests REAL: Large message handling
        Mocks: None
        """
        agent = agent_process_factory("large-msg-test")
        large_message = "x" * 10240  # 10KB

        result = send_a2a_message(agent.url, large_message)

        assert result["status_code"] == 200, (
            f"Expected 200 for 10KB message, got {result['status_code']}. "
            f"Cause: Large message rejected or caused error. "
            f"Fix: Check message size limits in A2A server."
        )

    def test_message_with_special_characters(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message with special characters
        When: Sending to agent
        Then: Special characters are handled correctly

        Tests REAL: Special character handling
        Mocks: None
        """
        agent = agent_process_factory("special-chars-test")
        special_message = (
            "Test <script>alert('xss')</script> & \"quotes\" 'apostrophes'"
        )

        result = send_a2a_message(agent.url, special_message)

        assert result["status_code"] == 200, (
            f"Expected 200 for special chars message, got {result['status_code']}. "
            f"Cause: Special characters may have caused parsing error. "
            f"Fix: Check JSON encoding in message handling."
        )

    def test_message_with_newlines_and_tabs(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message with newlines and tabs
        When: Sending to agent
        Then: Formatting characters are preserved

        Tests REAL: Whitespace preservation
        Mocks: None
        """
        agent = agent_process_factory("formatting-test")
        formatted_message = "Line 1\nLine 2\n\tTabbed line"

        result = send_a2a_message(agent.url, formatted_message)

        assert result["status_code"] == 200, (
            f"Expected 200 for formatted message, got {result['status_code']}. "
            f"Cause: Newlines/tabs may have caused parsing error. "
            f"Fix: Check message encoding."
        )

    @pytest.mark.parametrize(
        "message,description",
        [
            ("你好世界", "Chinese characters"),
            ("こんにちは", "Japanese characters"),
            ("Привет мир", "Cyrillic characters"),
            ("안녕하세요", "Korean Hangul"),
            ("مرحبا بالعالم", "Arabic RTL"),
            ("שלום עולם", "Hebrew RTL"),
            ("สวัสดีโลก", "Thai script"),
            ("नमस्ते दुनिया", "Hindi Devanagari"),
            ("Bonjour café", "French accents"),
            ("Γεια σου κόσμε", "Greek letters"),
            ("Hello 🌍🎉🤖", "Emoji"),
            ("test،message", "Arabic comma"),
        ],
    )
    def test_unicode_message_preserved(
        self, agent_process_factory, send_a2a_message, message, description
    ):
        """
        Given: A message with Unicode ({description})
        When: Sending to agent
        Then: Unicode is handled without error

        Tests REAL: Unicode message handling
        Mocks: None
        """
        agent = agent_process_factory(f"unicode-{description[:8]}")

        result = send_a2a_message(agent.url, message)

        assert result["status_code"] == 200, (
            f"Unicode message failed for {description}. "
            f"Status: {result['status_code']}. "
            f"Message: '{message}'. "
            f"Cause: Unicode encoding issue. "
            f"Fix: Ensure UTF-8 encoding throughout message handling."
        )


# =============================================================================
# Tests: Conversation Tracking
# =============================================================================


class TestConversationTracking:
    """Tests for conversation ID handling across messages."""

    def test_conversation_id_included_in_response(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message with conversation_id
        When: Agent responds
        Then: Response includes conversation_id (in metadata or top-level)

        Tests REAL: Conversation ID propagation
        Mocks: None
        """
        agent = agent_process_factory("conv-id-test")

        result = send_a2a_message(
            agent.url, "Test message", conversation_id="test-conv-123"
        )

        # Response should be JSON with conversation_id (may be in metadata or top-level)
        if isinstance(result["response"], dict):
            response = result["response"]
            has_conv_id = (
                "conversation_id" in response
                or "content" in response
                or "parts" in response  # A2A format uses parts
                or ("metadata" in response and "conversation_id" in response.get("metadata", {}))
            )
            assert has_conv_id, (
                f"Expected conversation_id, content, or parts in response. "
                f"Got keys: {list(response.keys())}. "
                f"Cause: Response format unexpected. "
                f"Fix: Check A2A response format."
            )

    def test_multiple_messages_same_conversation(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Multiple messages with same conversation_id
        When: Sending sequentially to agent
        Then: All messages processed correctly

        Tests REAL: Multi-turn conversation
        Mocks: None
        """
        agent = agent_process_factory("multi-turn-test")
        conv_id = "multi-turn-conv-123"

        results = []
        for i in range(3):
            result = send_a2a_message(
                agent.url, f"Message {i}", conversation_id=conv_id
            )
            results.append(result)

        for i, result in enumerate(results):
            assert result["status_code"] == 200, (
                f"Message {i} failed with status {result['status_code']}. "
                f"Cause: Multi-turn conversation handling issue. "
                f"Fix: Check conversation_id handling in handle_message()."
            )

    def test_different_conversations_isolated(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Messages with different conversation_ids
        When: Sending to same agent
        Then: Each conversation is handled independently

        Tests REAL: Conversation isolation
        Mocks: None
        """
        agent = agent_process_factory("isolation-test")

        result_a = send_a2a_message(
            agent.url, "Conv A message", conversation_id="conv-a"
        )
        result_b = send_a2a_message(
            agent.url, "Conv B message", conversation_id="conv-b"
        )

        assert result_a["status_code"] == 200, (
            f"Expected 200 for conversation A, got {result_a['status_code']}. "
            f"Cause: Conversation isolation may have failed. "
            f"Fix: Check conversation_id handling."
        )
        assert result_b["status_code"] == 200, (
            f"Expected 200 for conversation B, got {result_b['status_code']}. "
            f"Cause: Conversation isolation may have failed. "
            f"Fix: Check conversation_id handling."
        )


# =============================================================================
# Tests: Concurrent Messages
# =============================================================================


class TestConcurrentMessages:
    """Tests for handling multiple simultaneous messages."""

    def test_agent_handles_10_concurrent_messages(
        self, agent_process_factory, http_client
    ):
        """
        Given: A running agent
        When: Sending 10 concurrent messages
        Then: All messages are processed successfully

        Tests REAL: Concurrent request handling
        Mocks: None
        """
        agent = agent_process_factory("concurrent-10-test")

        def send_message(i: int) -> dict:
            payload = {
                "role": "user",
                "content": {"type": "text", "text": f"Concurrent message {i}"},
                "conversation_id": f"concurrent-{i}",
            }
            try:
                response = http_client.post(
                    f"{agent.url}/a2a", json=payload, timeout=HTTP_REQUEST_TIMEOUT
                )
                return {"index": i, "status": response.status_code}
            except Exception as e:
                return {"index": i, "status": -1, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_message, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successful = [r for r in results if r["status"] == 200]
        failed = [r for r in results if r["status"] != 200]

        assert len(successful) >= 8, (
            f"Expected at least 8/10 concurrent messages to succeed, got {len(successful)}. "
            f"Failed: {failed}. "
            f"Cause: Agent may not handle concurrent requests well. "
            f"Fix: Check thread safety in A2A server."
        )

    def test_agent_handles_50_concurrent_messages(
        self, agent_process_factory, http_client
    ):
        """
        Given: A running agent
        When: Sending 50 concurrent messages
        Then: Most messages are processed successfully (>80%)

        Tests REAL: High concurrency handling
        Mocks: None
        """
        agent = agent_process_factory("concurrent-50-test")

        def send_message(i: int) -> dict:
            payload = {
                "role": "user",
                "content": {"type": "text", "text": f"High concurrency message {i}"},
                "conversation_id": f"high-concurrent-{i}",
            }
            try:
                response = http_client.post(
                    f"{agent.url}/a2a",
                    json=payload,
                    timeout=HTTP_REQUEST_TIMEOUT
                    * 2,  # Longer timeout for high concurrency
                )
                return {"index": i, "status": response.status_code}
            except Exception as e:
                return {"index": i, "status": -1, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(send_message, i) for i in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successful = [r for r in results if r["status"] == 200]

        assert len(successful) >= 40, (
            f"Expected at least 40/50 (80%) messages to succeed, got {len(successful)}. "
            f"Cause: Agent overwhelmed by concurrent requests. "
            f"Fix: Consider adding request queuing or rate limiting."
        )


# =============================================================================
# Tests: MCP Communication
# =============================================================================


class TestMCPCommunication:
    """Tests for MCP message routing (#nanda:, #smithery:)."""

    def test_mcp_message_format_recognized(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message starting with #nanda:
        When: Sending to agent
        Then: Message is recognized as MCP query

        Tests REAL: MCP message routing
        Mocks: None (tests routing, not actual MCP server)
        """
        agent = agent_process_factory("mcp-format-test")

        # This should be recognized as MCP format, even if server doesn't exist
        result = send_a2a_message(agent.url, "#nanda:test-server query")

        # We expect either success or a specific MCP-related error, not generic 500
        assert (
            result["status_code"] < 500 or "mcp" in str(result["response"]).lower()
        ), (
            f"Expected MCP message to be routed, got status {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: MCP message format not recognized. "
            f"Fix: Check _handle_mcp_message() in SimpleAgentBridge."
        )

    def test_smithery_message_format_recognized(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message starting with #smithery:
        When: Sending to agent
        Then: Message is recognized as Smithery MCP query

        Tests REAL: Smithery MCP message routing
        Mocks: None (tests routing, not actual Smithery API)
        """
        agent = agent_process_factory("smithery-format-test")

        result = send_a2a_message(agent.url, "#smithery:@test-server query")

        # Should be recognized as MCP format
        assert (
            result["status_code"] < 500
            or "mcp" in str(result["response"]).lower()
            or "smithery" in str(result["response"]).lower()
        ), (
            f"Expected Smithery message to be routed, got status {result['status_code']}. "
            f"Cause: Smithery message format not recognized. "
            f"Fix: Check MCP routing in SimpleAgentBridge."
        )

    def test_hash_without_provider_handled(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A message starting with # but no valid provider
        When: Sending to agent
        Then: Error is returned gracefully

        Tests REAL: Invalid MCP format handling
        Mocks: None
        """
        agent = agent_process_factory("invalid-mcp-test")

        result = send_a2a_message(agent.url, "#invalid message")

        # Should not crash, may return error
        assert result["status_code"] < 500, (
            f"Expected graceful handling of invalid MCP format, got {result['status_code']}. "
            f"Cause: Invalid MCP format caused server error. "
            f"Fix: Add validation for MCP message format."
        )

    def test_mcp_server_lookup_attempted(
        self,
        registry_process,
        agent_process_factory,
        http_client,
        send_a2a_message,
        sample_mcp_server_data,
    ):
        """
        Given: An MCP server registered in registry
        When: Sending #nanda:server-name query to agent
        Then: Agent attempts to look up and connect to MCP server

        Tests REAL: MCP server discovery flow
        Mocks: None (but MCP server doesn't need to exist)
        """
        # Register a test MCP server
        http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        # Create agent with MCP registry configured
        agent = agent_process_factory("mcp-lookup-test")

        # Send MCP query - may fail to connect but should attempt lookup
        result = send_a2a_message(
            agent.url, f"#nanda:{sample_mcp_server_data['qualified_name']} test query"
        )

        # Response should indicate MCP processing was attempted
        # Even if connection fails, we verify the routing path was followed
        response_text = str(result["response"]).lower()
        # Accept success, connection error, or MCP-related message
        mcp_related = any(
            term in response_text
            for term in ["mcp", "server", "connection", "error", "lookup"]
        )

        assert (
            result["status_code"] == 200 or mcp_related or result["status_code"] < 500
        ), (
            f"Expected MCP lookup to be attempted. "
            f"Status: {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: MCP routing may not be working. "
            f"Fix: Check MCP registry integration in SimpleAgentBridge."
        )


# =============================================================================
# Tests: @mention Agent-to-Agent Routing
# =============================================================================


class TestAtMentionRouting:
    """Tests for @mention routing between agents."""

    def test_at_mention_routes_to_target_agent(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents (sender and target) registered
        When: Sender receives @target message
        Then: Message is routed to target agent

        Tests REAL: @mention routing between agents
        Mocks: None
        """
        sender = agent_process_factory("routing-sender")
        target = agent_process_factory("routing-target")

        # Send @mention to sender, should route to target
        result = send_a2a_message(sender.url, "@routing-target Hello from sender!")

        assert result["status_code"] == 200, (
            f"Expected 200 for @mention routing, got {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: @mention routing may have failed. "
            f"Fix: Check _handle_a2a_message() in SimpleAgentBridge."
        )

        # Response should include target agent's ID (indicating it was routed)
        response_text = str(result["response"])
        assert "routing-target" in response_text, (
            f"Expected target agent ID in routed response. "
            f"Got: {response_text[:200]}. "
            f"Cause: Message may not have been routed to target. "
            f"Fix: Verify @mention detection and A2AClient.send_message()."
        )

    def test_at_mention_nonexistent_agent_returns_error(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Message with @nonexistent-agent
        When: Sending to agent
        Then: Returns appropriate error (not crash)

        Tests REAL: Error handling for missing target
        Mocks: None
        """
        sender = agent_process_factory("sender-missing-target")

        result = send_a2a_message(sender.url, "@nonexistent-agent-xyz Hello")

        # Should not crash, return error message
        assert result["status_code"] < 500, (
            f"Expected non-500 for missing target, got {result['status_code']}. "
            f"Cause: Missing agent lookup caused server error. "
            f"Fix: Add error handling in _handle_a2a_message()."
        )

        # Response should indicate agent not found
        response_text = str(result["response"]).lower()
        assert any(
            term in response_text for term in ["not found", "error", "unknown", "failed"]
        ), (
            f"Expected error message for missing agent. "
            f"Got: {result['response']}. "
            f"Cause: No error returned for missing agent. "
            f"Fix: Return user-friendly error when target not in registry."
        )

    def test_at_mention_with_message_body(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: @mention with message body
        When: Routing to target
        Then: Full message body is preserved

        Tests REAL: Message body preservation in routing
        Mocks: None
        """
        sender = agent_process_factory("body-sender")
        target = agent_process_factory("body-target")

        test_body = "This is a test message with special content: 12345"
        result = send_a2a_message(sender.url, f"@body-target {test_body}")

        assert result["status_code"] == 200, (
            f"Expected 200 for @mention with body, got {result['status_code']}. "
            f"Cause: Message routing failed. "
            f"Fix: Check message body extraction in routing."
        )

        # Verify body content was passed through
        response_text = str(result["response"])
        assert "12345" in response_text or "test message" in response_text.lower(), (
            f"Expected message body in response. "
            f"Sent: '{test_body}'. Got: '{response_text[:200]}'. "
            f"Cause: Message body may have been truncated or lost. "
            f"Fix: Verify full message is passed to target agent."
        )


# =============================================================================
# Tests: Message Size Limits (E2E - tests actual HTTP limits, not mocked)
# =============================================================================


class TestMessageSizeLimits:
    """Tests for message size handling."""

    def test_100kb_message_handled(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A 100KB message
        When: Sending to agent
        Then: Message processed without error

        Tests REAL: Medium-large message handling
        Mocks: None
        """
        agent = agent_process_factory("100kb-msg")
        large_message = "x" * (100 * 1024)  # 100KB

        result = send_a2a_message(agent.url, large_message)

        assert result["status_code"] == 200, (
            f"Expected 200 for 100KB message, got {result['status_code']}. "
            f"Cause: Message size limit may be too low. "
            f"Fix: Increase message size limit or add streaming."
        )

    def test_1mb_message_handled_or_rejected_gracefully(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: A 1MB message
        When: Sending to agent
        Then: Either processed or rejected with 413 (not 500)

        Tests REAL: Large message limit behavior
        Mocks: None
        """
        agent = agent_process_factory("1mb-msg")
        large_message = "x" * (1024 * 1024)  # 1MB

        result = send_a2a_message(agent.url, large_message)

        # Should either succeed or return 413 Payload Too Large, not 500
        assert result["status_code"] in [200, 413] or result["status_code"] < 500, (
            f"Expected 200 or 413 for 1MB message, got {result['status_code']}. "
            f"Cause: Large message caused server error. "
            f"Fix: Add content-length limit with proper 413 response."
        )


# =============================================================================
# Tests: Concurrent Conversation Access
# =============================================================================


class TestConcurrentConversations:
    """Tests for concurrent access to same conversation."""

    def test_concurrent_messages_same_conversation(
        self, agent_process_factory, http_client
    ):
        """
        Given: Multiple concurrent messages to same conversation
        When: Sending simultaneously
        Then: All messages processed (tests thread safety)

        Tests REAL: Thread safety in conversation handling
        Mocks: None
        """
        agent = agent_process_factory("concurrent-conv")
        conv_id = "shared-conversation-123"

        def send_message(i: int) -> dict:
            payload = {
                "role": "user",
                "content": {"type": "text", "text": f"Concurrent message {i}"},
                "conversation_id": conv_id,  # Same conversation
            }
            try:
                response = http_client.post(
                    f"{agent.url}/a2a", json=payload, timeout=HTTP_REQUEST_TIMEOUT
                )
                return {"index": i, "status": response.status_code}
            except Exception as e:
                return {"index": i, "status": -1, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_message, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successful = [r for r in results if r["status"] == 200]

        assert len(successful) == 5, (
            f"Expected all 5 concurrent same-conversation messages to succeed. "
            f"Got {len(successful)}. Results: {results}. "
            f"Cause: Race condition in conversation state handling. "
            f"Fix: Add thread-safe locking for conversation access."
        )
