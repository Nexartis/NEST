#!/usr/bin/env python3
"""
Comprehensive tests for A2A Protocol Implementation (PR #12)

Tests three critical areas:
1. Backward compatibility with previous A2A implementation
2. Official A2A protocol support (new implementation)
3. Resource cleanup functionality (PR #12 fix)

Run with: pytest tests/test_protocols/test_a2a_protocol.py -v

Error Scenarios Tested:
- Event loop handling in sync/async contexts
- HTTP client lifecycle management
- Protocol router integration
- Resource cleanup on errors
"""

import pytest
import asyncio
import sys
from nanda_core.core.adapter import NANDA
from nanda_core.protocols.a2a.protocol import A2AProtocol
from nanda_core.protocols.router import ProtocolRouter


# Test agent logic
def simple_agent_logic(message: str, conversation_id: str) -> str:
    """Simple echo agent for testing"""
    return f"Echo: {message}"


class TestA2AProtocolBackwardCompatibility:
    """
    Test backward compatibility with previous A2A implementation

    Purpose: Ensure existing code doesn't break with the new protocol architecture

    Potential Issues:
    - Missing protocol registration
    - Router not initialized
    - Bridge not connected to router
    """

    def test_nanda_initialization_default(self):
        """
        Test that NANDA initializes with A2A protocol by default

        Expected: A2A protocol should be auto-registered

        Failure Reasons:
        - Protocol not registered → Check ProtocolRouter.register()
        - Wrong protocol name → Check A2AProtocol.get_protocol_name()
        """
        try:
            agent = NANDA(
                agent_id="test-backward-compat",
                agent_logic=simple_agent_logic,
                port=6000,
                host="127.0.0.1",
                public_url="http://127.0.0.1:6000",
                enable_telemetry=False
            )

            # Should have A2A protocol registered
            assert "a2a" in agent.router.get_all_protocols(), \
                "A2A protocol not registered. Check NANDA.__init__() protocol setup"

            protocol = agent.router.get_protocol("a2a")
            assert protocol is not None, \
                "A2A protocol registered but not retrievable. Check ProtocolRouter.get_protocol()"

        except Exception as e:
            pytest.fail(f"NANDA initialization failed: {e}\n"
                       f"Possible cause: Missing dependencies or protocol registration error")

    def test_agent_has_router(self):
        """
        Test that agent has protocol router

        Expected: Agent should have router attribute of type ProtocolRouter

        Failure Reasons:
        - Router not initialized → Check NANDA.__init__()
        - Wrong router type → Check import statements
        """
        agent = NANDA(
            agent_id="test-router",
            agent_logic=simple_agent_logic,
            port=6000,
            host="127.0.0.1",
            public_url="http://127.0.0.1:6000",
            enable_telemetry=False
        )

        assert hasattr(agent, 'router'), \
            "Agent missing 'router' attribute. Check NANDA.__init__()"

        assert isinstance(agent.router, ProtocolRouter), \
            f"Router is {type(agent.router)}, expected ProtocolRouter"

    def test_agent_bridge_integration(self):
        """
        Test that agent bridge integrates with protocol router

        Expected: Bridge should have router reference

        Failure Reasons:
        - Bridge not initialized → Check NANDA.__init__()
        - Router not passed to bridge → Check AgentBridge.__init__()
        """
        agent = NANDA(
            agent_id="test-bridge",
            agent_logic=simple_agent_logic,
            port=6000,
            host="127.0.0.1",
            public_url="http://127.0.0.1:6000",
            enable_telemetry=False
        )

        assert hasattr(agent, 'bridge'), \
            "Agent missing 'bridge' attribute"

        assert hasattr(agent.bridge, 'router'), \
            "Bridge missing 'router' attribute. Check AgentBridge integration"


class TestOfficialA2AProtocol:
    """
    Test official A2A protocol implementation

    Purpose: Verify the new A2A SDK integration works correctly

    Dependencies:
    - a2a-sdk >= 0.2.0
    - httpx >= 0.27.0
    """

    def test_a2a_protocol_initialization(self):
        """
        Test A2A protocol initializes correctly

        Expected: Protocol should store agent metadata

        Failure Reasons:
        - Missing required parameters → Check A2AProtocol.__init__() signature
        - AgentCard creation fails → Check a2a-sdk installation
        """
        try:
            protocol = A2AProtocol(
                agent_id="test-agent",
                agent_name="Test Agent",
                public_url="http://localhost:6000",
                domain="testing",
                specialization="test agent",
                description="Test description",
                capabilities=["text"]
            )

            assert protocol.agent_id == "test-agent", "Agent ID mismatch"
            assert protocol.agent_name == "Test Agent", "Agent name mismatch"
            assert protocol.get_protocol_name() == "a2a", "Protocol name should be 'a2a'"

        except ImportError as e:
            pytest.fail(f"A2A SDK import failed: {e}\n"
                       f"Solution: pip install a2a-sdk>=0.2.0")

    def test_a2a_protocol_has_httpx_client(self):
        """
        Test that A2A protocol creates HTTP client

        Expected: httpx.AsyncClient should be initialized

        Failure Reasons:
        - httpx not installed → pip install httpx>=0.27.0
        - Client not initialized → Check A2AProtocol.__init__()
        """
        protocol = A2AProtocol(
            agent_id="test-agent",
            agent_name="Test Agent",
            public_url="http://localhost:6000"
        )

        assert hasattr(protocol, 'httpx_client'), \
            "Protocol missing 'httpx_client' attribute"

        assert protocol.httpx_client is not None, \
            "HTTP client is None. Check A2AProtocol.__init__()"

        assert not protocol.httpx_client.is_closed, \
            "HTTP client should not be closed after initialization"

    def test_a2a_protocol_agent_card(self):
        """
        Test that A2A protocol creates AgentCard

        Expected: AgentCard with correct metadata

        Failure Reasons:
        - AgentCard not created → Check a2a.types import
        - Metadata mismatch → Check AgentCard construction
        """
        protocol = A2AProtocol(
            agent_id="test-agent",
            agent_name="Test Agent",
            public_url="http://localhost:6000",
            domain="testing",
            description="Test description"
        )

        assert hasattr(protocol, 'agent_card'), \
            "Protocol missing 'agent_card' attribute"

        assert protocol.agent_card.name == "Test Agent", \
            f"AgentCard name mismatch: {protocol.agent_card.name}"

        assert protocol.agent_card.description == "Test description", \
            f"AgentCard description mismatch: {protocol.agent_card.description}"

    def test_a2a_protocol_metadata(self):
        """
        Test A2A protocol metadata generation

        Expected: Metadata dict with agent info and capabilities

        Failure Reasons:
        - get_metadata() returns wrong format
        - Missing required fields
        """
        protocol = A2AProtocol(
            agent_id="test-agent",
            agent_name="Test Agent",
            public_url="http://localhost:6000",
            capabilities=["text", "image"]
        )

        metadata = protocol.get_metadata()

        assert "agent_id" in metadata, "Metadata missing 'agent_id'"
        assert metadata["agent_id"] == "test-agent"

        assert "name" in metadata, "Metadata missing 'name'"
        assert metadata["name"] == "Test Agent"

        assert "capabilities" in metadata, "Metadata missing 'capabilities'"
        assert "text" in metadata["capabilities"], "'text' not in capabilities"
        assert "image" in metadata["capabilities"], "'image' not in capabilities"

    @pytest.mark.asyncio
    async def test_a2a_protocol_incoming_handler(self):
        """
        Test setting incoming message handler

        Expected: Server components should be initialized after setting handler

        Failure Reasons:
        - Handler not set → Check set_incoming_handler()
        - Server components not initialized → Check A2AStarletteApplication creation
        """
        protocol = A2AProtocol(
            agent_id="test-agent",
            agent_name="Test Agent",
            public_url="http://localhost:6000"
        )

        # Set handler
        async def test_handler(message: dict) -> dict:
            return {"response": "test"}

        protocol.set_incoming_handler(test_handler)

        # Should initialize server components
        assert protocol.incoming_handler is not None, \
            "Handler not set after set_incoming_handler()"

        assert protocol.agent_executor is not None, \
            "AgentExecutor not initialized. Check NANDAAgentExecutor creation"

        assert protocol.request_handler is not None, \
            "RequestHandler not initialized. Check DefaultRequestHandler creation"

        assert protocol.server_app is not None, \
            "Server app not initialized. Check A2AStarletteApplication creation"


class TestResourceCleanup:
    """
    Test resource cleanup functionality (PR #12 fix)

    Purpose: Verify HTTP clients and other resources are properly released

    Critical: Resource leaks can cause:
    - Socket exhaustion
    - Memory leaks
    - Connection pool issues
    """

    @pytest.mark.asyncio
    async def test_a2a_protocol_cleanup(self):
        """
        Test that A2A protocol cleanup closes HTTP client

        Expected: HTTP client should be closed after cleanup()

        Failure Reasons:
        - cleanup() not implemented → Check A2AProtocol.cleanup()
        - aclose() not called → Check httpx_client.aclose() call
        """
        protocol = A2AProtocol(
            agent_id="test-cleanup",
            agent_name="Test Cleanup",
            public_url="http://localhost:6000"
        )

        # Client should be open
        assert protocol.httpx_client is not None, "HTTP client is None"
        assert not protocol.httpx_client.is_closed, \
            "HTTP client should not be closed before cleanup"

        # Cleanup
        await protocol.cleanup()

        # Client should be closed
        assert protocol.httpx_client.is_closed, \
            "HTTP client not closed after cleanup(). Check A2AProtocol.cleanup() implementation"

    @pytest.mark.asyncio
    async def test_protocol_router_cleanup_all(self):
        """
        Test that ProtocolRouter cleans up all protocols

        Expected: All registered protocols should be cleaned up

        Failure Reasons:
        - cleanup_all() not implemented → Check ProtocolRouter.cleanup_all()
        - Not iterating all protocols → Check iteration logic
        """
        router = ProtocolRouter()

        # Register A2A protocol
        protocol = A2AProtocol(
            agent_id="test-router-cleanup",
            agent_name="Test Router Cleanup",
            public_url="http://localhost:6000"
        )
        router.register(protocol)

        # Client should be open
        assert not protocol.httpx_client.is_closed, \
            "HTTP client should not be closed before router cleanup"

        # Cleanup all
        await router.cleanup_all()

        # Client should be closed
        assert protocol.httpx_client.is_closed, \
            "HTTP client not closed after router.cleanup_all(). " \
            "Check ProtocolRouter.cleanup_all() implementation"

    def test_nanda_stop_calls_cleanup(self):
        """
        Test that NANDA.stop() triggers protocol cleanup

        Expected: stop() should cleanup all protocol resources

        Failure Reasons:
        - stop() doesn't call cleanup → Check NANDA.stop()
        - Event loop handling issue → Check asyncio.get_running_loop() logic
        - asyncio.run() not called in sync context → Check RuntimeError handling

        Context: This test runs in pytest (sync context), so stop() should
        create a temporary event loop to run cleanup.
        """
        agent = NANDA(
            agent_id="test-stop-cleanup",
            agent_logic=simple_agent_logic,
            port=6000,
            host="127.0.0.1",
            public_url="http://127.0.0.1:6000",
            enable_telemetry=False
        )

        # Get protocol
        protocol = agent.router.get_protocol("a2a")
        assert protocol is not None, "A2A protocol not found"
        assert not protocol.httpx_client.is_closed, \
            "HTTP client should not be closed before stop()"

        # Stop agent (should trigger cleanup)
        try:
            agent.stop()
        except Exception as e:
            pytest.fail(f"agent.stop() raised exception: {e}\n"
                       f"Check NANDA.stop() error handling")

        # HTTP client should be closed
        assert protocol.httpx_client.is_closed, \
            "HTTP client not closed after stop(). " \
            "Possible causes:\n" \
            "1. cleanup() not called → Check NANDA.stop() implementation\n" \
            "2. Event loop issue → Check asyncio.get_running_loop() / asyncio.run() logic\n" \
            "3. RuntimeError not caught → Check try-except around get_running_loop()"

    @pytest.mark.asyncio
    async def test_cleanup_handles_errors_gracefully(self):
        """
        Test that cleanup handles errors without crashing

        Expected: cleanup_all() should continue even if one protocol fails

        Failure Reasons:
        - Exception not caught → Check try-except in cleanup_all()
        - Error propagates → Should print warning, not raise
        """
        router = ProtocolRouter()

        # Create a mock protocol that raises error on cleanup
        class MockProtocol:
            def get_protocol_name(self):
                return "mock"

            async def cleanup(self):
                raise Exception("Test cleanup error")

        router.protocols["mock"] = MockProtocol()

        # Cleanup should not raise exception
        try:
            await router.cleanup_all()
            success = True
        except Exception as e:
            success = False
            pytest.fail(f"cleanup_all() should handle errors gracefully, but raised: {e}\n"
                       f"Check ProtocolRouter.cleanup_all() error handling")

        assert success, "cleanup_all() should not raise exceptions"

    @pytest.mark.asyncio
    async def test_cleanup_in_async_context(self):
        """
        Test cleanup when called from async context

        Expected: Should use create_task() instead of asyncio.run()

        Note: This test verifies the async context path in NANDA.stop()
        """
        agent = NANDA(
            agent_id="test-async-cleanup",
            agent_logic=simple_agent_logic,
            port=6000,
            host="127.0.0.1",
            public_url="http://127.0.0.1:6000",
            enable_telemetry=False
        )

        protocol = agent.router.get_protocol("a2a")

        # In async context, stop() should work without errors
        agent.stop()

        # Wait a bit for the task to complete
        await asyncio.sleep(0.1)

        # Note: In async context, create_task() is used, so cleanup happens asynchronously
        # We can't guarantee client is closed immediately


class TestIntegration:
    """
    Integration tests for complete agent lifecycle

    Purpose: Test real-world usage scenarios end-to-end
    """

    def test_full_agent_lifecycle(self):
        """
        Test complete agent lifecycle: create → use → stop

        Expected: Agent should initialize, work, and cleanup properly

        This is the most important integration test. If this fails, check:
        1. Agent initialization
        2. Protocol registration
        3. Resource cleanup
        """
        # Create
        try:
            agent = NANDA(
                agent_id="test-lifecycle",
                agent_logic=simple_agent_logic,
                agent_name="Lifecycle Test",
                domain="testing",
                port=6000,
                host="127.0.0.1",
                public_url="http://127.0.0.1:6000",
                enable_telemetry=False
            )
        except Exception as e:
            pytest.fail(f"Agent creation failed: {e}")

        # Verify initialization
        assert agent.agent_id == "test-lifecycle"
        assert "a2a" in agent.router.get_all_protocols(), \
            "A2A protocol not registered during initialization"

        # Get protocol
        protocol = agent.router.get_protocol("a2a")
        assert protocol is not None, "A2A protocol not retrievable"
        assert not protocol.httpx_client.is_closed, \
            "HTTP client closed prematurely"

        # Stop (cleanup)
        try:
            agent.stop()
        except Exception as e:
            pytest.fail(f"Agent stop failed: {e}\n"
                       f"Check NANDA.stop() implementation and error handling")

        # Verify cleanup
        assert protocol.httpx_client.is_closed, \
            "HTTP client not closed after stop().\n" \
            f"Test environment: Python {sys.version}\n" \
            f"This indicates the resource cleanup fix (PR #12) may not be working.\n" \
            f"Check NANDA.stop() event loop handling."

    def test_multiple_agents_cleanup(self):
        """
        Test cleanup with multiple agents

        Expected: Each agent should cleanup its own resources
        """
        agents = []

        # Create multiple agents
        for i in range(3):
            agent = NANDA(
                agent_id=f"test-agent-{i}",
                agent_logic=simple_agent_logic,
                port=6000 + i,
                host="127.0.0.1",
                public_url=f"http://127.0.0.1:{6000 + i}",
                enable_telemetry=False
            )
            agents.append(agent)

        # Get all protocols
        protocols = [agent.router.get_protocol("a2a") for agent in agents]

        # All clients should be open
        for protocol in protocols:
            assert not protocol.httpx_client.is_closed

        # Stop all agents
        for agent in agents:
            agent.stop()

        # All clients should be closed
        for i, protocol in enumerate(protocols):
            assert protocol.httpx_client.is_closed, \
                f"Agent {i} HTTP client not closed"


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])
