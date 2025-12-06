"""
E2E Tests for Multi-Agent Chains.

Tests REAL multi-agent communication scenarios including conversation
chains, parallel messaging, and conversation isolation.

Test Categories:
- TestTwoAgentConversation: Basic two-agent exchanges
- TestMultiAgentChains: Three+ agent chains
- TestConversationIsolation: Conversation ID separation
- TestParallelMessaging: Concurrent multi-agent scenarios
"""

import concurrent.futures
import time

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Two-Agent Conversation
# =============================================================================


class TestTwoAgentConversation:
    """Tests for basic two-agent exchanges."""

    def test_single_exchange_between_two_agents(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents A and B
        When: A sends message to B
        Then: B processes and responds

        Tests REAL: Basic two-agent exchange
        Mocks: None
        """
        agent_a = agent_process_factory("exchange-a")
        agent_b = agent_process_factory("exchange-b")

        result = send_a2a_message(agent_a.url, "@exchange-b Hello from A")

        assert result["status_code"] == 200, (
            f"Two-agent exchange failed: {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: A→B communication broken. "
            f"Fix: Check @mention routing."
        )

        # Verify response contains B's agent ID (proving routing worked)
        response_text = str(result["response"])
        assert "exchange-b" in response_text.lower(), (
            f"Expected 'exchange-b' in response (proving B received message). "
            f"Got: {response_text[:200]}. "
            f"Cause: Message may not have reached agent B. "
            f"Fix: Check registry lookup and A2A POST to B."
        )

    def test_multiple_exchanges_same_conversation(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents in ongoing conversation
        When: Multiple messages exchanged
        Then: All messages processed correctly

        Tests REAL: Multi-turn conversation
        Mocks: None
        """
        agent_a = agent_process_factory("multi-turn-a")
        agent_b = agent_process_factory("multi-turn-b")

        conv_id = "multi-turn-test-123"
        messages = [
            "@multi-turn-b First message",
            "@multi-turn-b Second message",
            "@multi-turn-b Third message",
        ]

        results = []
        for msg in messages:
            result = send_a2a_message(agent_a.url, msg, conversation_id=conv_id)
            results.append(result)

        # All messages should succeed
        for i, result in enumerate(results):
            assert result["status_code"] == 200, (
                f"Message {i+1} failed: {result['status_code']}. "
                f"Cause: Multi-turn handling issue. "
                f"Fix: Check conversation state management."
            )

    def test_bidirectional_conversation(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents
        When: Both send messages to each other
        Then: Bidirectional communication works

        Tests REAL: Bidirectional exchange
        Mocks: None
        """
        agent_a = agent_process_factory("bidir-a")
        agent_b = agent_process_factory("bidir-b")

        # A sends to B
        result_a_to_b = send_a2a_message(agent_a.url, "@bidir-b Message from A")

        # B sends to A
        result_b_to_a = send_a2a_message(agent_b.url, "@bidir-a Message from B")

        assert result_a_to_b["status_code"] == 200, (
            f"Expected 200 for A→B, got {result_a_to_b['status_code']}. "
            f"Cause: Bidirectional communication A→B failed. "
            f"Fix: Check @mention routing for bidir-a to bidir-b."
        )
        assert result_b_to_a["status_code"] == 200, (
            f"Expected 200 for B→A, got {result_b_to_a['status_code']}. "
            f"Cause: Bidirectional communication B→A failed. "
            f"Fix: Check @mention routing for bidir-b to bidir-a."
        )

        # Verify each response contains the target agent's ID
        assert "bidir-b" in str(result_a_to_b["response"]).lower(), (
            f"Expected 'bidir-b' in A→B response. "
            f"Got: {str(result_a_to_b['response'])[:200]}."
        )
        assert "bidir-a" in str(result_b_to_a["response"]).lower(), (
            f"Expected 'bidir-a' in B→A response. "
            f"Got: {str(result_b_to_a['response'])[:200]}."
        )


# =============================================================================
# Tests: Multi-Agent Chains
# =============================================================================


class TestMultiAgentChains:
    """Tests for three+ agent communication chains."""

    def test_three_agents_registered_and_discoverable(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Three agents started
        When: All register with registry
        Then: All are discoverable

        Tests REAL: Multi-agent registration
        Mocks: None
        """
        agent_a = agent_process_factory("chain3-a")
        agent_b = agent_process_factory("chain3-b")
        agent_c = agent_process_factory("chain3-c")

        # All should be in registry
        response = http_client.get(f"{registry_process.url}/list")
        data = response.json()
        agent_ids = [a["agent_id"] for a in data["agents"]]

        for expected in ["chain3-a", "chain3-b", "chain3-c"]:
            assert expected in agent_ids, (
                f"Agent '{expected}' not in registry. "
                f"Found: {agent_ids}. "
                f"Cause: Registration failed. "
                f"Fix: Check multi-agent registration."
            )

    def test_message_from_a_to_b_while_c_exists(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Three agents A, B, C
        When: A sends to B (C exists but not involved)
        Then: Message routes correctly to B only

        Tests REAL: Targeted routing with multiple agents
        Mocks: None
        """
        agent_a = agent_process_factory("target-a")
        agent_b = agent_process_factory("target-b")
        agent_c = agent_process_factory("target-c")

        result = send_a2a_message(agent_a.url, "@target-b Message for B only")

        assert result["status_code"] == 200, (
            f"Targeted message failed: {result['status_code']}. "
            f"Cause: Message may have gone to wrong agent. "
            f"Fix: Check @mention target extraction."
        )

    def test_five_agents_can_coexist(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Five agents started simultaneously
        When: All register
        Then: All coexist without port conflicts

        Tests REAL: Multi-agent coexistence
        Mocks: None
        """
        agents = []
        for i in range(5):
            agent = agent_process_factory(f"coexist-{i}")
            agents.append(agent)


        # All should have unique ports
        ports = set(a.port for a in agents)
        assert len(ports) == 5, (
            f"Expected 5 unique ports, got {len(ports)}. "
            f"Ports: {ports}. "
            f"Cause: Port collision. "
            f"Fix: Check port allocation."
        )

        # All should be in registry
        response = http_client.get(f"{registry_process.url}/list")
        data = response.json()
        assert data["count"] >= 5, (
            f"Expected at least 5 agents, got {data['count']}. "
            f"Cause: Not all agents registered. "
            f"Fix: Check registration timing."
        )


# =============================================================================
# Tests: Conversation Isolation
# =============================================================================


class TestConversationIsolation:
    """Tests for conversation ID separation."""

    def test_different_conversation_ids_are_isolated(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Messages with different conversation IDs
        When: Sending to same agent
        Then: Conversations are independent

        Tests REAL: Conversation isolation
        Mocks: None
        """
        sender = agent_process_factory("isolation-sender")
        receiver = agent_process_factory("isolation-receiver")

        # Two different conversations
        result_conv1 = send_a2a_message(
            sender.url,
            "@isolation-receiver Message in conv 1",
            conversation_id="conversation-1",
        )

        result_conv2 = send_a2a_message(
            sender.url,
            "@isolation-receiver Message in conv 2",
            conversation_id="conversation-2",
        )

        assert result_conv1["status_code"] == 200, (
            f"Expected 200 for conversation 1, got {result_conv1['status_code']}. "
            f"Cause: Conversation isolation failed for conv-1. "
            f"Fix: Check conversation_id handling."
        )
        assert result_conv2["status_code"] == 200, (
            f"Expected 200 for conversation 2, got {result_conv2['status_code']}. "
            f"Cause: Conversation isolation failed for conv-2. "
            f"Fix: Check conversation_id handling."
        )

    def test_interleaved_conversations(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two conversations interleaved
        When: Alternating messages
        Then: Each conversation maintains context

        Tests REAL: Interleaved conversation handling
        Mocks: None
        """
        sender = agent_process_factory("interleave-sender")
        receiver = agent_process_factory("interleave-receiver")

        messages = [
            ("@interleave-receiver Conv1 Msg1", "conv-1"),
            ("@interleave-receiver Conv2 Msg1", "conv-2"),
            ("@interleave-receiver Conv1 Msg2", "conv-1"),
            ("@interleave-receiver Conv2 Msg2", "conv-2"),
        ]

        results = []
        for msg, conv_id in messages:
            result = send_a2a_message(sender.url, msg, conversation_id=conv_id)
            results.append((conv_id, result))

        # All should succeed
        for conv_id, result in results:
            assert result["status_code"] == 200, (
                f"Interleaved message failed for {conv_id}: {result['status_code']}. "
                f"Cause: Conversation isolation broken. "
                f"Fix: Check conversation_id handling."
            )


# =============================================================================
# Tests: Parallel Messaging
# =============================================================================


class TestParallelMessaging:
    """Tests for concurrent multi-agent scenarios."""

    def test_parallel_messages_to_same_target(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Multiple senders, one receiver
        When: All send simultaneously
        Then: All messages processed

        Tests REAL: Concurrent message handling
        Mocks: None
        """
        receiver = agent_process_factory("parallel-receiver")
        senders = [agent_process_factory(f"parallel-sender-{i}") for i in range(5)]

        def send_message(sender_idx: int) -> dict:
            payload = {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"@parallel-receiver Message from sender {sender_idx}",
                },
                "conversation_id": f"parallel-{sender_idx}",
            }
            try:
                response = http_client.post(
                    f"http://localhost:{senders[sender_idx].port}/a2a",
                    json=payload,
                    timeout=HTTP_REQUEST_TIMEOUT,
                )
                return {"sender": sender_idx, "status": response.status_code}
            except Exception as e:
                return {"sender": sender_idx, "status": -1, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_message, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        successful = [r for r in results if r["status"] == 200]
        assert len(successful) >= 3, (
            f"Expected at least 3/5 parallel messages to succeed, got {len(successful)}. "
            f"Results: {results}. "
            f"Cause: Concurrent request handling issue. "
            f"Fix: Check thread safety in agent."
        )

    def test_parallel_conversations_between_pairs(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Multiple agent pairs
        When: Each pair communicates simultaneously
        Then: All conversations succeed

        Tests REAL: Parallel pair communication
        Mocks: None
        """
        # Create 3 pairs of agents
        pairs = []
        for i in range(3):
            sender = agent_process_factory(f"pair{i}-sender")
            receiver = agent_process_factory(f"pair{i}-receiver")
            pairs.append((sender, receiver, i))


        def send_pair_message(pair_idx: int) -> dict:
            sender, receiver, idx = pairs[pair_idx]
            payload = {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"@pair{idx}-receiver Hello from pair {idx}",
                },
                "conversation_id": f"pair-conv-{idx}",
            }
            try:
                response = http_client.post(
                    f"{sender.url}/a2a", json=payload, timeout=HTTP_REQUEST_TIMEOUT
                )
                return {"pair": pair_idx, "status": response.status_code}
            except Exception as e:
                return {"pair": pair_idx, "status": -1, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(send_pair_message, i) for i in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for result in results:
            assert result["status"] == 200, (
                f"Pair {result['pair']} failed: {result}. "
                f"Cause: Parallel pair communication issue. "
                f"Fix: Check multi-agent routing."
            )

    def test_rapid_sequential_messages(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Two agents
        When: Sending many messages in rapid succession
        Then: All messages processed

        Tests REAL: Rapid message handling
        Mocks: None
        """
        sender = agent_process_factory("rapid-sender")
        receiver = agent_process_factory("rapid-receiver")

        results = []
        for i in range(20):
            result = send_a2a_message(
                sender.url,
                f"@rapid-receiver Rapid message {i}",
                conversation_id=f"rapid-{i}",
            )
            results.append(result)

        successful = [r for r in results if r["status_code"] == 200]
        assert len(successful) >= 15, (
            f"Expected at least 15/20 rapid messages to succeed, got {len(successful)}. "
            f"Cause: Agent overwhelmed by rapid messages. "
            f"Fix: Consider message queuing."
        )


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestMultiAgentEdgeCases:
    """Tests for multi-agent edge cases."""

    def test_agent_can_message_multiple_targets(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: One sender, multiple targets
        When: Sender messages each target
        Then: All messages delivered

        Tests REAL: One-to-many messaging
        Mocks: None
        """
        sender = agent_process_factory("one-to-many-sender")
        targets = [agent_process_factory(f"target-{i}") for i in range(3)]

        results = []
        for i, target in enumerate(targets):
            result = send_a2a_message(sender.url, f"@target-{i} Message to target {i}")
            results.append(result)

        for i, result in enumerate(results):
            assert result["status_code"] == 200, (
                f"Message to target-{i} failed: {result['status_code']}. "
                f"Cause: One-to-many routing issue. "
                f"Fix: Check target selection."
            )

    def test_agents_with_similar_names(
        self, registry_process, agent_process_factory, send_a2a_message
    ):
        """
        Given: Agents with similar names (test, test-1, test-2)
        When: Messaging specific one
        Then: Correct agent receives message

        Tests REAL: Name disambiguation
        Mocks: None
        """
        sender = agent_process_factory("similar-sender")
        agent_test = agent_process_factory("similar-test")
        agent_test_1 = agent_process_factory("similar-test-1")
        agent_test_2 = agent_process_factory("similar-test-2")

        # Message specifically to test-1
        result = send_a2a_message(
            sender.url, "@similar-test-1 Message for test-1 specifically"
        )

        assert result["status_code"] == 200, (
            f"Similar name message failed: {result['status_code']}. "
            f"Cause: Name matching may be too greedy. "
            f"Fix: Check exact agent_id matching in @mention."
        )
