"""
E2E Tests for Agent Lifecycle.

Tests REAL agent startup, registration, health checks, and shutdown.
Uses actual subprocess spawning and HTTP communication.

Test Categories:
- TestAgentStartup: Agent process startup and port binding
- TestAgentRegistration: Registration with registry server
- TestAgentHealthCheck: Health and status endpoints
- TestAgentShutdown: Graceful shutdown and cleanup
- TestMCPAgentLifecycle: MCP-enabled agent lifecycle
"""

import signal
import subprocess
import time

import pytest
import requests

from tests.e2e.conftest import (
    HTTP_REQUEST_TIMEOUT,
    PROCESS_STARTUP_TIMEOUT,
    find_free_port,
    is_port_in_use,
)

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Agent Startup
# =============================================================================


class TestAgentStartup:
    """Tests for agent process startup and port binding."""

    def test_agent_starts_on_specified_port(self, agent_process_factory):
        """
        Given: A specified port number
        When: Starting an agent on that port
        Then: Agent process binds to the specified port

        Tests REAL: Process spawning, port binding
        Mocks: None
        """
        port = find_free_port()
        agent = agent_process_factory("startup-test", port=port)

        assert agent.port == port, (
            f"Expected agent on port {port}, got {agent.port}. "
            f"Cause: Port assignment failed. "
            f"Fix: Check port availability before starting agent."
        )
        assert is_port_in_use(port), (
            f"Expected port {port} to be in use, but it's not. "
            f"Cause: Agent may have crashed or failed to bind. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

    def test_agent_auto_assigns_port_when_not_specified(self, agent_process_factory):
        """
        Given: No port specified
        When: Starting an agent
        Then: Agent is assigned a free port automatically

        Tests REAL: Port auto-assignment, process startup
        Mocks: None
        """
        agent = agent_process_factory("auto-port-test")

        assert agent.port > 0, (
            f"Expected positive port number, got {agent.port}. "
            f"Cause: Port auto-assignment failed. "
            f"Fix: Check find_free_port() implementation."
        )
        assert is_port_in_use(agent.port), (
            f"Expected port {agent.port} to be in use. "
            f"Cause: Agent failed to start. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

    def test_agent_starts_within_timeout(self, agent_process_factory):
        """
        Given: An agent configuration
        When: Starting the agent
        Then: Agent starts within PROCESS_STARTUP_TIMEOUT seconds

        Tests REAL: Startup time performance
        Mocks: None
        """
        agent = agent_process_factory("timeout-test")

        assert agent.startup_time < PROCESS_STARTUP_TIMEOUT, (
            f"Expected startup time < {PROCESS_STARTUP_TIMEOUT}s, got {agent.startup_time:.2f}s. "
            f"Cause: Agent startup is too slow. "
            f"Fix: Profile agent initialization and optimize imports."
        )

    def test_multiple_agents_start_on_different_ports(self, agent_process_factory):
        """
        Given: Multiple agent configurations
        When: Starting multiple agents
        Then: Each agent gets a unique port and all are running

        Tests REAL: Multiple process management, port isolation
        Mocks: None
        """
        agent_a = agent_process_factory("multi-agent-a")
        agent_b = agent_process_factory("multi-agent-b")
        agent_c = agent_process_factory("multi-agent-c")

        ports = {agent_a.port, agent_b.port, agent_c.port}
        assert len(ports) == 3, (
            f"Expected 3 unique ports, got {len(ports)}: {ports}. "
            f"Cause: Port collision between agents. "
            f"Fix: Check find_free_port() is called for each agent."
        )

        for agent in [agent_a, agent_b, agent_c]:
            assert is_port_in_use(agent.port), (
                f"Agent {agent.name} not running on port {agent.port}. "
                f"Cause: Agent process may have crashed. "
                f"Fix: Check agent logs at {agent.log_file}"
            )


# =============================================================================
# Tests: Agent Registration
# =============================================================================


class TestAgentRegistration:
    """Tests for agent registration with registry server."""

    def test_agent_registers_with_registry_on_startup(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: A registry server running
        When: Starting an agent with registry_url configured
        Then: Agent is registered in the registry

        Tests REAL: HTTP POST to registry, registration flow
        Mocks: None
        """
        agent = agent_process_factory("register-test")

        # Give time for registration to complete

        # Verify agent is in registry
        response = http_client.get(f"{registry_process.url}/lookup/register-test")

        assert response.status_code == 200, (
            f"Expected 200 from registry lookup, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            f"Cause: Agent may not have registered. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

        data = response.json()
        assert data["agent_id"] == "register-test", (
            f"Expected agent_id='register-test', got '{data.get('agent_id')}'. "
            f"Cause: Registration data mismatch. "
            f"Fix: Check NANDA._register() implementation."
        )

    def test_agent_registration_includes_url(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: An agent with public_url configured
        When: Agent registers with registry
        Then: Registration includes the correct agent_url

        Tests REAL: Registration payload construction
        Mocks: None
        """
        agent = agent_process_factory("url-test")

        response = http_client.get(f"{registry_process.url}/lookup/url-test")
        data = response.json()

        assert "agent_url" in data, (
            f"Expected 'agent_url' in registration data, got keys: {list(data.keys())}. "
            f"Cause: agent_url not included in registration. "
            f"Fix: Check NANDA._register() payload."
        )
        assert f":{agent.port}" in data["agent_url"], (
            f"Expected port {agent.port} in agent_url, got '{data['agent_url']}'. "
            f"Cause: public_url not set correctly. "
            f"Fix: Check public_url construction in agent_process_factory."
        )

    def test_agent_appears_in_registry_list(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Multiple registered agents
        When: Listing agents from registry
        Then: All agents appear in the list

        Tests REAL: Registry list endpoint, multiple registrations
        Mocks: None
        """
        agent_a = agent_process_factory("list-test-a")
        agent_b = agent_process_factory("list-test-b")

        response = http_client.get(f"{registry_process.url}/list")
        assert response.status_code == 200, (
            f"Expected 200 from /list, got {response.status_code}. "
            f"Cause: Registry list endpoint failed. "
            f"Fix: Check registry_server.py /list endpoint."
        )

        data = response.json()
        agent_ids = [a["agent_id"] for a in data["agents"]]

        assert "list-test-a" in agent_ids, (
            f"Expected 'list-test-a' in agent list, got {agent_ids}. "
            f"Cause: Agent A not registered. "
            f"Fix: Check registration flow."
        )
        assert "list-test-b" in agent_ids, (
            f"Expected 'list-test-b' in agent list, got {agent_ids}. "
            f"Cause: Agent B not registered. "
            f"Fix: Check registration flow."
        )

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("simple-agent", "simple alphanumeric"),
            ("agent-with-hyphens", "hyphenated"),
            ("agent_with_underscores", "underscored"),
            ("Agent123", "mixed case with numbers"),
        ],
    )
    def test_agent_id_formats_register_correctly(
        self,
        registry_process,
        agent_process_factory,
        http_client,
        agent_id,
        description,
    ):
        """
        Given: Various agent_id formats ({description})
        When: Agent registers with registry
        Then: agent_id is preserved exactly

        Tests REAL: agent_id handling in registration
        Mocks: None
        """
        agent = agent_process_factory(agent_id)

        response = http_client.get(f"{registry_process.url}/lookup/{agent_id}")
        assert response.status_code == 200, (
            f"Registration failed for {description} agent_id '{agent_id}'. "
            f"Status: {response.status_code}. "
            f"Cause: agent_id may have been rejected or modified. "
            f"Fix: Check agent_id validation in registry."
        )


# =============================================================================
# Tests: Agent Health Check
# =============================================================================


class TestAgentHealthCheck:
    """Tests for agent health and status endpoints."""

    def test_registry_health_check_returns_200(self, registry_process, http_client):
        """
        Given: A running registry server
        When: Calling /health endpoint
        Then: Returns 200 with status ok

        Tests REAL: Registry health endpoint
        Mocks: None
        """
        response = http_client.get(f"{registry_process.url}/health")

        assert response.status_code == 200, (
            f"Expected 200 from /health, got {response.status_code}. "
            f"Cause: Registry health check failed. "
            f"Fix: Check registry_server.py /health endpoint."
        )

        data = response.json()
        assert data.get("status") == "ok", (
            f"Expected status='ok', got '{data.get('status')}'. "
            f"Cause: Health check returned unhealthy status. "
            f"Fix: Check registry health logic."
        )

    def test_registry_stats_returns_agent_count(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Agents registered with registry
        When: Calling /stats endpoint
        Then: Returns correct agent count

        Tests REAL: Registry stats endpoint
        Mocks: None
        """
        agent_a = agent_process_factory("stats-test-a")
        agent_b = agent_process_factory("stats-test-b")

        response = http_client.get(f"{registry_process.url}/stats")
        assert response.status_code == 200, (
            f"Expected 200 from /stats, got {response.status_code}. "
            f"Cause: Stats endpoint failed. "
            f"Fix: Check registry_server.py /stats endpoint."
        )

        data = response.json()
        assert data.get("total_agents") >= 2, (
            f"Expected at least 2 agents in stats, got {data.get('total_agents')}. "
            f"Cause: Agents not counted correctly. "
            f"Fix: Check registry stats logic."
        )


# =============================================================================
# Tests: Agent Shutdown
# =============================================================================


class TestAgentShutdown:
    """Tests for agent graceful shutdown and cleanup."""

    def test_agent_process_terminates_on_sigterm(self, agent_process_factory):
        """
        Given: A running agent process
        When: Sending SIGTERM
        Then: Process terminates within 5 seconds

        Tests REAL: Process termination handling
        Mocks: None
        """
        agent = agent_process_factory("shutdown-test")

        # Verify running
        assert agent.process.poll() is None, "Agent should be running before shutdown"

        # Send SIGTERM
        agent.process.terminate()

        # Wait for termination
        try:
            agent.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent.process.kill()
            pytest.fail(
                f"Agent did not terminate within 5s after SIGTERM. "
                f"Cause: Agent may not handle SIGTERM properly. "
                f"Fix: Check signal handling in agent code."
            )

        assert agent.process.poll() is not None, (
            "Expected process to be terminated. "
            "Cause: Process still running after SIGTERM. "
            "Fix: Check NANDA.stop() implementation."
        )

    def test_port_released_after_agent_shutdown(self, agent_process_factory):
        """
        Given: An agent running on a specific port
        When: Agent is shutdown
        Then: Port is released and available for reuse

        Tests REAL: Port release on shutdown
        Mocks: None
        """
        port = find_free_port()
        agent = agent_process_factory("port-release-test", port=port)

        # Verify port in use
        assert is_port_in_use(port), "Port should be in use while agent running"

        # Shutdown agent
        agent.process.terminate()
        agent.process.wait(timeout=5)

        # Give OS time to release port

        # Verify port released
        assert not is_port_in_use(port), (
            f"Expected port {port} to be released after shutdown. "
            f"Cause: Socket may not have been closed properly. "
            f"Fix: Check socket cleanup in agent shutdown."
        )


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestAgentLifecycleEdgeCases:
    """Tests for edge cases in agent lifecycle."""

    def test_agent_with_very_long_agent_id(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: An agent_id with 100 characters
        When: Agent starts and registers
        Then: Long agent_id is handled correctly

        Tests REAL: Long agent_id handling
        Mocks: None
        """
        long_id = "agent-" + "x" * 94  # 100 chars total
        agent = agent_process_factory(long_id)

        response = http_client.get(f"{registry_process.url}/lookup/{long_id}")
        assert response.status_code == 200, (
            f"Expected 200 for long agent_id lookup, got {response.status_code}. "
            f"Cause: Long agent_id may have been truncated or rejected. "
            f"Fix: Check agent_id length limits in registry."
        )

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("café-agent", "French accents"),
            ("agent-日本語", "Japanese characters"),
            ("агент-тест", "Cyrillic characters"),
        ],
    )
    def test_unicode_agent_id_lifecycle(
        self,
        registry_process,
        agent_process_factory,
        http_client,
        agent_id,
        description,
    ):
        """
        Given: An agent_id with Unicode characters ({description})
        When: Agent starts and registers
        Then: Unicode agent_id is preserved

        Tests REAL: Unicode handling in registration
        Mocks: None
        """
        agent = agent_process_factory(agent_id)

        # URL-encode for lookup
        import urllib.parse

        encoded_id = urllib.parse.quote(agent_id, safe="")

        response = http_client.get(f"{registry_process.url}/lookup/{encoded_id}")
        assert response.status_code == 200, (
            f"Unicode agent_id lookup failed for {description}. "
            f"Status: {response.status_code}. "
            f"Cause: Unicode not handled correctly in URL. "
            f"Fix: Check URL encoding in registry lookup."
        )


# =============================================================================
# Tests: MCP Agent Lifecycle
# =============================================================================


class TestMCPAgentLifecycle:
    """Tests for MCP-enabled agent lifecycle."""

    def test_mcp_server_registers_with_registry(
        self, registry_process, http_client, sample_mcp_server_data
    ):
        """
        Given: MCP server registration data
        When: Registering MCP server with registry
        Then: MCP server is stored and retrievable

        Tests REAL: MCP server registration endpoint
        Mocks: None
        """
        # Register MCP server
        response = http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        assert response.status_code == 200, (
            f"Expected 200 from MCP server registration, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            f"Cause: MCP server registration failed. "
            f"Fix: Check registry_server.py /mcp_servers POST endpoint."
        )

        # Verify retrievable
        lookup_response = http_client.get(
            f"{registry_process.url}/mcp_servers/{sample_mcp_server_data['qualified_name']}"
        )

        assert lookup_response.status_code == 200, (
            f"Expected 200 from MCP server lookup, got {lookup_response.status_code}. "
            f"Cause: MCP server not stored correctly. "
            f"Fix: Check MCP server storage in registry."
        )

    def test_mcp_server_list_returns_registered_servers(
        self, registry_process, http_client, sample_mcp_server_data
    ):
        """
        Given: Registered MCP servers
        When: Listing MCP servers
        Then: All registered servers appear in list

        Tests REAL: MCP server list endpoint
        Mocks: None
        """
        # Register MCP server
        http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        # List servers
        response = http_client.get(f"{registry_process.url}/mcp_servers")

        assert response.status_code == 200, (
            f"Expected 200 from MCP servers list, got {response.status_code}. "
            f"Cause: MCP servers list endpoint failed. "
            f"Fix: Check registry_server.py /mcp_servers GET endpoint."
        )

        data = response.json()
        server_names = [s["qualified_name"] for s in data["servers"]]

        assert sample_mcp_server_data["qualified_name"] in server_names, (
            f"Expected '{sample_mcp_server_data['qualified_name']}' in server list. "
            f"Got: {server_names}. "
            f"Cause: MCP server not in list. "
            f"Fix: Check MCP server list logic."
        )
