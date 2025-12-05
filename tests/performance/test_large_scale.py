"""
Performance tests for large-scale scenarios.

Tests system behavior with many agents and messages.
These tests are marked as 'slow' and can be skipped for quick test runs.
"""

import pytest


@pytest.mark.slow
class TestLargeScaleScenarios:
    """Test scenarios with many agents (marked as slow)"""

    def test_many_agents_registration(self, agent_test_harness):
        """
        Test registering many agents.

        Verifies that the system can handle 100 agents being registered
        and can successfully look them up afterward.
        """
        num_agents = 100

        # Register 100 agents
        for i in range(num_agents):
            agent_id = f"agent-{i:04d}"
            agent_test_harness.register_test_agent(
                agent_id,
                display_name=f"Agent {i}",
                index=i
            )

        # Verify all agents are registered
        for i in range(num_agents):
            agent_id = f"agent-{i:04d}"
            agent = agent_test_harness.registry.lookup_agent(agent_id)
            assert agent is not None, f"Agent {agent_id} not found"
            assert agent["index"] == i, f"Agent {agent_id} has wrong index"

    def test_many_messages(self, agent_test_harness):
        """
        Test sending many messages.

        Verifies that the system can handle 1000 messages being sent
        to a single agent and track them all correctly.
        """
        receiver_id = "agent-receiver"
        num_messages = 1000

        # Send 1000 messages
        for i in range(num_messages):
            message = {"seq": i, "data": f"message-{i}"}
            agent_test_harness.adapter.send_message(receiver_id, message)

        # Verify all messages were tracked
        messages = agent_test_harness.adapter.get_messages(receiver_id)
        assert len(messages) == num_messages, \
            f"Expected {num_messages} messages, got {len(messages)}"
