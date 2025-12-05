"""
Shared pytest fixtures for NEST tests.

Combines SimpleAgentBridge-specific fixtures (from PR #24 by srcJin)
with generic agent testing infrastructure (from PR #20 by Sharathvc23).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from python_a2a import Message, TextContent, MessageRole
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4


# ============================================================================
# SimpleAgentBridge-Specific Fixtures (from PR #24)
# ============================================================================

@pytest.fixture
def mock_agent_logic():
    """Mock agent logic function that returns a simple response."""
    def agent_logic(message: str, conversation_id: str) -> str:
        return f"Response to: {message}"
    return agent_logic


@pytest.fixture
def mock_telemetry():
    """Mock telemetry system."""
    telemetry = Mock()
    telemetry.log_message_received = Mock()
    telemetry.log_message_sent = Mock()
    return telemetry


@pytest.fixture
def sample_text_message():
    """Create a sample text message for testing."""
    def _create_message(text: str, conversation_id: str = "test-conv-123"):
        return Message(
            role=MessageRole.USER,
            content=TextContent(text=text),
            conversation_id=conversation_id
        )
    return _create_message


@pytest.fixture
def mock_registry_response():
    """Mock response from agent registry lookup."""
    return {
        "agent_id": "test-agent",
        "agent_url": "http://localhost:6001",
        "name": "Test Agent",
        "status": "active"
    }


@pytest.fixture
def mock_requests_get():
    """Patch requests.get for registry lookups."""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_a2a_client():
    """Mock A2A client for agent-to-agent communication."""
    with patch('nanda_core.core.agent_bridge.A2AClient') as mock_client:
        yield mock_client


# ============================================================================
# Generic Agent Testing Infrastructure (from PR #20)
# ============================================================================

@pytest.fixture
def mock_registry():
    """
    Mock registry service for testing without external dependencies.
    Provides in-memory agent registration and lookup.

    Contributed by: Sharathvc23 (PR #20)
    """
    class MockRegistry:
        def __init__(self):
            self.agents: Dict[str, Dict[str, Any]] = {}
            self.delegations: Dict[str, Dict[str, Any]] = {}

        def register_agent(self, agent_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            """Register an agent with metadata"""
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
            return {"status": "registered", "agent_id": agent_id}

        def lookup_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
            """Lookup agent by ID"""
            return self.agents.get(agent_id)

        def grant_delegation(self, delegation: Dict[str, Any]) -> Dict[str, Any]:
            """Grant delegation to agent"""
            delegation_id = delegation.get("delegation_id", f"del:{uuid4().hex[:8]}")
            self.delegations[delegation_id] = delegation
            return {"status": "granted", "delegation_id": delegation_id}

        def verify_delegation(self, agent_id: str, action: str) -> bool:
            """Check if agent has delegation for action"""
            for delegation in self.delegations.values():
                if delegation.get("delegate", {}).get("agent_id") == agent_id:
                    scopes = delegation.get("scope", [])
                    if any(s.get("action") == action for s in scopes):
                        return True
            return False

        def reset(self):
            """Clear all data"""
            self.agents.clear()
            self.delegations.clear()

    registry = MockRegistry()
    return registry


@pytest.fixture
def mock_adapter():
    """
    Mock adapter service for testing agent-to-agent communication.
    Simulates message passing without external services.

    Contributed by: Sharathvc23 (PR #20)
    """
    class MockAdapter:
        def __init__(self):
            self.messages: List[Dict[str, Any]] = []
            self.responses: Dict[str, Any] = {}

        def send_message(self, to_agent: str, message: Dict[str, Any]) -> Dict[str, Any]:
            """Send message to agent"""
            message_id = f"msg:{uuid4().hex[:8]}"
            self.messages.append({
                "message_id": message_id,
                "to_agent": to_agent,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # Return pre-configured response if available
            return self.responses.get(to_agent, {"status": "sent", "message_id": message_id})

        def configure_response(self, agent_id: str, response: Dict[str, Any]):
            """Configure mock response for specific agent"""
            self.responses[agent_id] = response

        def get_messages(self, to_agent: Optional[str] = None) -> List[Dict[str, Any]]:
            """Retrieve sent messages"""
            if to_agent:
                return [m for m in self.messages if m["to_agent"] == to_agent]
            return self.messages

        def reset(self):
            """Clear all messages"""
            self.messages.clear()
            self.responses.clear()

    adapter = MockAdapter()
    return adapter


@pytest.fixture
def agent_test_harness(mock_registry, mock_adapter):
    """
    Complete test harness combining registry and adapter mocks.
    Provides a full testing environment for agent development.

    Contributed by: Sharathvc23 (PR #20)

    Usage:
        def test_agent(agent_test_harness):
            # Register agent
            agent_test_harness.register_test_agent(
                "my-agent",
                capabilities=["task1", "task2"]
            )

            # Test functionality
            agent = agent_test_harness.registry.lookup_agent("my-agent")
            assert "task1" in agent["capabilities"]
    """
    class AgentTestHarness:
        def __init__(self, registry, adapter):
            self.registry = registry
            self.adapter = adapter

        def register_test_agent(self, agent_id: str, **metadata):
            """Register a test agent with given metadata"""
            return self.registry.register_agent(agent_id, metadata)

        def send_test_message(self, to_agent: str, message: str, **kwargs):
            """Send a test message to agent"""
            return self.adapter.send_message(to_agent, {"content": message, **kwargs})

        def configure_agent_response(self, agent_id: str, response: Dict[str, Any]):
            """Configure mock response for agent"""
            self.adapter.configure_response(agent_id, response)

        def get_agent_messages(self, agent_id: str) -> List[Dict[str, Any]]:
            """Get all messages sent to agent"""
            return self.adapter.get_messages(agent_id)

        def setup_agent_with_delegation(self, agent_id: str, actions: List[str]) -> Dict[str, Any]:
            """Helper to setup agent with specific delegations"""
            self.registry.register_agent(agent_id, {
                "display_name": f"Agent {agent_id}",
                "capabilities": actions
            })

            delegation = {
                "delegation_id": f"del:{agent_id}:{uuid4().hex[:8]}",
                "delegate": {"agent_id": agent_id},
                "scope": [{"action": action, "resource": "*"} for action in actions]
            }
            self.registry.grant_delegation(delegation)

            return {
                "agent_id": agent_id,
                "delegation": delegation
            }

        def simulate_agent_message(self, from_agent: str, to_agent: str, message: Dict[str, Any]) -> Dict[str, Any]:
            """Helper to simulate agent-to-agent communication"""
            return self.adapter.send_message(to_agent, {
                "from": from_agent,
                **message
            })

        def reset(self):
            """Reset harness state"""
            self.registry.reset()
            self.adapter.reset()

    return AgentTestHarness(mock_registry, mock_adapter)


# ============================================================================
# Sample Data Fixtures (from PR #20)
# ============================================================================

@pytest.fixture
def sample_delegation():
    """Sample delegation for testing"""
    return {
        "delegation_id": "del:abc123",
        "delegator": {"agent_id": "delegator-agent"},
        "delegate": {"agent_id": "delegate-agent"},
        "scope": [{"action": "read"}, {"action": "write"}]
    }


@pytest.fixture
def sample_agent_metadata():
    """Sample agent metadata for testing"""
    return {
        "display_name": "Test Agent",
        "capabilities": ["data_processing", "analysis"],
        "labels": ["test", "example"],
        "metadata": {
            "version": "1.0.0",
            "environment": "test"
        }
    }
