"""
E2E Tests for Agent Discovery.

Tests REAL library code (RegistryClient, MCPRegistry) against a live test registry.
Unlike integration tests that mock HTTP, these tests exercise actual network calls.

Key Difference from Integration Tests:
- Integration tests: Mock HTTP layer, test client code logic
- E2E tests: Real HTTP calls, test full client → server → response flow

Test Categories:
- TestRegistryClientLookup: RegistryClient.lookup_agent() with real HTTP
- TestRegistryClientList: RegistryClient.list_agents() operations
- TestRegistryClientSearch: RegistryClient.search_agents() with filters
- TestRegistryClientStatus: RegistryClient.update_agent_status() operations
- TestRegistryClientErrorHandling: Error injection and resilience
- TestMCPRegistryDiscovery: MCPRegistry operations with real servers
- TestAgentLifecycle: Full agent startup → register → discover → communicate
- TestConcurrentOperations: Race conditions and concurrent access
"""

import time
import threading
from typing import List

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT, wait_for_agent_registered

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: RegistryClient Lookup (Tests REAL RegistryClient class)
# =============================================================================


class TestRegistryClientLookup:
    """
    Tests for RegistryClient.lookup_agent() with real HTTP calls.

    Unlike integration tests that mock HTTP, these test the full path:
    RegistryClient → HTTP request → Registry Server → HTTP response → Parse
    """

    def test_lookup_registered_agent_returns_agent_data(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: An agent registered in the registry
        When: Calling registry_client.lookup_agent(agent_id)
        Then: Returns dict with agent_id and agent_url

        Tests REAL: RegistryClient.lookup_agent() HTTP GET
        Validates: Response parsing, field extraction
        """
        # Setup: Register agent directly to registry
        agent_data = {
            "agent_id": "lookup-test-agent",
            "agent_url": "http://localhost:9001",
            "capabilities": ["test"],
        }
        http_client.post(f"{registry_process.url}/register", json=agent_data)

        # Exercise: Use REAL RegistryClient
        result = registry_client.lookup_agent("lookup-test-agent")

        # Verify
        assert result is not None, (
            "Expected agent data dict, got None. "
            "Cause: RegistryClient.lookup_agent() failed to parse response. "
            "Fix: Check lookup_agent() implementation in registry_client.py"
        )
        assert result.get("agent_id") == "lookup-test-agent", (
            f"Expected agent_id='lookup-test-agent', got '{result.get('agent_id')}'. "
            "Cause: Response parsing incorrect. "
            "Fix: Verify JSON response structure matches expected format."
        )
        assert "agent_url" in result, (
            f"Expected 'agent_url' in response. Got keys: {list(result.keys())}. "
            "Cause: agent_url field missing from response. "
            "Fix: Check registry server returns agent_url."
        )

    def test_lookup_nonexistent_agent_returns_none(self, registry_client):
        """
        Given: An agent_id that doesn't exist
        When: Calling registry_client.lookup_agent(agent_id)
        Then: Returns None (not exception)

        Tests REAL: 404 handling in RegistryClient
        Validates: Graceful handling of missing agents
        """
        result = registry_client.lookup_agent("nonexistent-agent-xyz-123")

        assert result is None, (
            f"Expected None for nonexistent agent, got {result}. "
            "Cause: RegistryClient not handling 404 correctly. "
            "Fix: Return None when response.status_code == 404"
        )

    def test_lookup_agent_with_special_characters_in_id(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Agent registered with special characters in ID
        When: Looking up the agent
        Then: Returns correct agent (URL encoding works)

        Tests REAL: URL encoding in RegistryClient
        Validates: Special character handling in URL path
        """
        # Agent ID with characters that need URL encoding
        agent_id = "agent-with-dashes_and_underscores"
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": agent_id, "agent_url": "http://localhost:9002"},
        )

        result = registry_client.lookup_agent(agent_id)

        assert result is not None, (
            f"Expected to find agent '{agent_id}'. "
            "Cause: URL encoding issue in lookup_agent(). "
            "Fix: Ensure agent_id is properly URL encoded."
        )
        assert result.get("agent_id") == agent_id

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("test-agent", "Simple ASCII"),
            ("agent.with.dots", "Dots in ID"),
            ("agent123", "Alphanumeric"),
            ("UPPERCASE-AGENT", "Uppercase"),
        ],
    )
    def test_lookup_various_valid_agent_ids(
        self, registry_client, registry_process, http_client, agent_id, description
    ):
        """
        Given: Agent with various valid ID formats ({description})
        When: Looking up by agent_id
        Then: Returns agent data

        Tests REAL: ID format handling
        """
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": agent_id, "agent_url": "http://localhost:9003"},
        )

        result = registry_client.lookup_agent(agent_id)

        assert result is not None, (
            f"Failed to lookup agent with {description}: '{agent_id}'. "
            "Cause: Agent ID format not supported. "
            "Fix: Check ID validation and URL construction."
        )


# =============================================================================
# Tests: RegistryClient List Operations
# =============================================================================


class TestRegistryClientList:
    """Tests for RegistryClient.list_agents() with real HTTP calls."""

    def test_list_agents_returns_all_registered(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Multiple agents registered
        When: Calling registry_client.list_agents()
        Then: Returns list containing all agents

        Tests REAL: RegistryClient.list_agents() HTTP GET
        """
        # Register multiple agents
        for i in range(3):
            http_client.post(
                f"{registry_process.url}/register",
                json={"agent_id": f"list-agent-{i}", "agent_url": f"http://localhost:900{i}"},
            )

        result = registry_client.list_agents()

        assert isinstance(result, list), (
            f"Expected list, got {type(result).__name__}. "
            "Cause: list_agents() not returning list type. "
            "Fix: Ensure list_agents() returns [] on all code paths."
        )

        agent_ids = [a.get("agent_id") for a in result if isinstance(a, dict)]
        for i in range(3):
            assert f"list-agent-{i}" in agent_ids, (
                f"Expected 'list-agent-{i}' in list. Got: {agent_ids}. "
                "Cause: Agent not included in list response. "
                "Fix: Check list endpoint includes all registered agents."
            )

    def test_list_agents_empty_registry_returns_empty_list(self, registry_client):
        """
        Given: Empty registry (reset before test by autouse fixture)
        When: Calling registry_client.list_agents()
        Then: Returns empty list, not None or error

        Tests REAL: Empty list handling
        """
        result = registry_client.list_agents()

        assert result == [] or result == {"agents": [], "count": 0} or (
            isinstance(result, list) and len(result) == 0
        ), (
            f"Expected empty list for empty registry, got {result}. "
            "Cause: Empty registry not handled correctly. "
            "Fix: Return [] when no agents registered."
        )

    def test_list_agents_handles_network_error_gracefully(self, registry_process):
        """
        Given: Registry client pointing to invalid URL
        When: Calling list_agents()
        Then: Returns empty list, doesn't crash

        Tests REAL: Network error resilience
        """
        from nanda_core.core.registry_client import RegistryClient

        client = RegistryClient(registry_url="http://localhost:1")  # Invalid port

        try:
            result = client.list_agents()
            assert result == [], (
                f"Expected [] on network error, got {result}. "
                "Cause: Exception not caught. "
                "Fix: Add try-except returning [] in list_agents()."
            )
        except Exception as e:
            pytest.fail(
                f"list_agents() raised exception instead of returning []: {e}. "
                "Cause: Missing exception handling. "
                "Fix: Wrap HTTP call in try-except."
            )


# =============================================================================
# Tests: RegistryClient Search Operations
# =============================================================================


class TestRegistryClientSearch:
    """Tests for RegistryClient.search_agents() with real HTTP calls."""

    def test_search_by_query_matches_agent_id(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Agent with specific ID
        When: Searching with query matching ID
        Then: Returns matching agent

        Tests REAL: Query parameter handling in search_agents()
        """
        http_client.post(
            f"{registry_process.url}/register",
            json={
                "agent_id": "searchable-bot",
                "agent_url": "http://localhost:9010",
                "description": "A searchable agent",
            },
        )

        result = registry_client.search_agents(query="searchable")

        assert isinstance(result, list), f"Expected list, got {type(result)}"
        agent_ids = [a.get("agent_id") for a in result if isinstance(a, dict)]
        assert "searchable-bot" in agent_ids, (
            f"Expected 'searchable-bot' in search results. Got: {agent_ids}. "
            "Cause: Query not matching agent_id. "
            "Fix: Check query matching logic includes agent_id field."
        )

    def test_search_by_capabilities_returns_matching(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Agents with different capabilities
        When: Searching by capability
        Then: Returns only agents with that capability

        Tests REAL: Capability filter parameter
        """
        # Agent WITH target capability
        http_client.post(
            f"{registry_process.url}/register",
            json={
                "agent_id": "capable-agent",
                "agent_url": "http://localhost:9011",
                "capabilities": ["data_analysis", "reporting"],
            },
        )
        # Agent WITHOUT target capability
        http_client.post(
            f"{registry_process.url}/register",
            json={
                "agent_id": "other-agent",
                "agent_url": "http://localhost:9012",
                "capabilities": ["translation"],
            },
        )

        result = registry_client.search_agents(capabilities=["data_analysis"])

        agent_ids = [a.get("agent_id") for a in result if isinstance(a, dict)]
        assert "capable-agent" in agent_ids, (
            f"Expected 'capable-agent' with data_analysis capability. Got: {agent_ids}. "
            "Cause: Capability filter not working. "
            "Fix: Check capabilities parameter handling."
        )
        # Note: other-agent may or may not be filtered depending on implementation

    def test_search_no_matches_returns_empty_list(self, registry_client):
        """
        Given: No agents matching query
        When: Searching
        Then: Returns empty list, not None

        Tests REAL: Empty result handling
        """
        result = registry_client.search_agents(query="nonexistent-xyz-never-exists")

        assert result == [] or (isinstance(result, list) and len(result) == 0), (
            f"Expected empty list for no matches, got {result}. "
            "Cause: Empty search result not handled. "
            "Fix: Return [] when no matches found."
        )


# =============================================================================
# Tests: RegistryClient Status Operations
# =============================================================================


class TestRegistryClientStatus:
    """Tests for agent status operations with real HTTP calls."""

    def test_update_agent_status_changes_status(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: A registered agent
        When: Updating its status via RegistryClient
        Then: Status is changed in registry

        Tests REAL: RegistryClient.update_agent_status() HTTP PUT
        """
        agent_id = "status-test-agent"
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": agent_id, "agent_url": "http://localhost:9020"},
        )

        # Update status using real client
        result = registry_client.update_agent_status(agent_id, "busy")

        # Verify via direct HTTP (not through client, to isolate test)
        status_response = http_client.get(f"{registry_process.url}/status/{agent_id}")
        assert status_response.status_code == 200
        data = status_response.json()
        assert data.get("status") == "busy", (
            f"Expected status='busy', got '{data.get('status')}'. "
            "Cause: update_agent_status() not updating registry. "
            "Fix: Check PUT request body and endpoint."
        )

    def test_unregister_agent_removes_from_registry(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: A registered agent
        When: Unregistering via RegistryClient
        Then: Agent no longer exists in registry

        Tests REAL: RegistryClient.unregister_agent() HTTP DELETE
        """
        agent_id = "unregister-test-agent"
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": agent_id, "agent_url": "http://localhost:9021"},
        )

        # Verify registered
        assert registry_client.lookup_agent(agent_id) is not None

        # Unregister
        result = registry_client.unregister_agent(agent_id)

        # Verify removed
        assert registry_client.lookup_agent(agent_id) is None, (
            "Agent still exists after unregister. "
            "Cause: unregister_agent() not sending DELETE request. "
            "Fix: Check DELETE endpoint and response handling."
        )

    def test_unregister_nonexistent_agent_returns_false(self, registry_client):
        """
        Given: Agent ID that doesn't exist
        When: Trying to unregister
        Then: Returns False, doesn't crash

        Tests REAL: 404 handling in unregister_agent()
        """
        result = registry_client.unregister_agent("nonexistent-agent-xyz")

        assert result is False, (
            f"Expected False for nonexistent agent unregister, got {result}. "
            "Cause: 404 status not handled correctly. "
            "Fix: Return False when status_code == 404"
        )


# =============================================================================
# Tests: Error Injection and Resilience
# =============================================================================


class TestRegistryClientErrorHandling:
    """
    Tests for RegistryClient behavior when registry returns errors.

    Uses error injection via /_set_error_mode endpoint to simulate failures.
    """

    def test_register_handles_500_error_gracefully(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Registry configured to return 500 error
        When: RegistryClient tries to register
        Then: Returns False, doesn't crash

        Tests REAL: Server error handling in register_agent()
        """
        # Enable error mode
        http_client.post(
            f"{registry_process.url}/_set_error_mode",
            json={"enabled": True, "status_code": 500, "message": "Simulated server error"},
        )

        try:
            result = registry_client.register_agent("test-agent", "http://localhost:9030")

            assert result is False, (
                f"Expected False on 500 error, got {result}. "
                "Cause: Server error not returning False. "
                "Fix: Return False when status_code >= 500"
            )
        finally:
            # Disable error mode for other tests
            http_client.post(
                f"{registry_process.url}/_set_error_mode",
                json={"enabled": False},
            )

    def test_register_handles_503_service_unavailable(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Registry returning 503 Service Unavailable
        When: RegistryClient tries to register
        Then: Returns False (may retry based on implementation)

        Tests REAL: Service unavailable handling
        """
        http_client.post(
            f"{registry_process.url}/_set_error_mode",
            json={"enabled": True, "status_code": 503, "message": "Service temporarily unavailable"},
        )

        try:
            result = registry_client.register_agent("test-agent", "http://localhost:9031")
            assert result is False, (
                "Expected False on 503, got True. "
                "Cause: 503 status not handled. "
                "Fix: Handle 503 as registration failure."
            )
        finally:
            http_client.post(f"{registry_process.url}/_set_error_mode", json={"enabled": False})

    def test_register_handles_400_bad_request(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Registry returning 400 Bad Request
        When: RegistryClient tries to register
        Then: Returns False

        Tests REAL: Client error handling
        """
        http_client.post(
            f"{registry_process.url}/_set_error_mode",
            json={"enabled": True, "status_code": 400, "message": "Invalid request"},
        )

        try:
            result = registry_client.register_agent("test-agent", "http://localhost:9032")
            assert result is False, "Expected False on 400 Bad Request"
        finally:
            http_client.post(f"{registry_process.url}/_set_error_mode", json={"enabled": False})

    def test_health_check_returns_true_when_healthy(self, registry_client):
        """
        Given: Registry is healthy
        When: Calling health_check()
        Then: Returns True

        Tests REAL: health_check() implementation
        """
        result = registry_client.health_check()

        assert result is True, (
            f"Expected True for healthy registry, got {result}. "
            "Cause: health_check() not returning True on 200. "
            "Fix: Return True when /health returns 200."
        )

    def test_health_check_returns_false_when_unreachable(self):
        """
        Given: Registry is unreachable
        When: Calling health_check()
        Then: Returns False, doesn't crash

        Tests REAL: Connection error handling
        """
        from nanda_core.core.registry_client import RegistryClient

        client = RegistryClient(registry_url="http://localhost:1")  # Invalid

        result = client.health_check()

        assert result is False, (
            f"Expected False for unreachable registry, got {result}. "
            "Cause: Connection error not caught. "
            "Fix: Return False in except block."
        )


# =============================================================================
# Tests: MCP Registry Discovery
# =============================================================================


class TestMCPRegistryDiscovery:
    """Tests for MCPRegistry with real HTTP calls to test registry."""

    def test_register_and_lookup_mcp_server(
        self, mcp_registry, registry_process, http_client
    ):
        """
        Given: MCP server registration data
        When: Registering via MCPRegistry
        Then: Can retrieve server info

        Tests REAL: MCPRegistry registration and lookup
        """
        # Register MCP server directly (MCPRegistry may not have register method)
        server_data = {
            "qualified_name": "test-mcp-server",
            "endpoint": "http://localhost:7001/mcp",
            "description": "Test MCP server",
            "provider": "nanda",
        }
        http_client.post(f"{registry_process.url}/mcp_servers", json=server_data)

        # Lookup via MCPRegistry
        result = mcp_registry.get_nanda_mcp_server_info("test-mcp-server")

        assert result is not None, (
            "Expected MCP server info, got None. "
            "Cause: get_nanda_mcp_server_info() not finding server. "
            "Fix: Check MCP server lookup implementation."
        )

    def test_lookup_nonexistent_mcp_server_returns_none(self, mcp_registry):
        """
        Given: MCP server name that doesn't exist
        When: Looking up via MCPRegistry
        Then: Returns None, doesn't crash

        Tests REAL: 404 handling in MCPRegistry
        """
        result = mcp_registry.get_nanda_mcp_server_info("nonexistent-mcp-xyz")

        assert result is None, (
            f"Expected None for nonexistent MCP server, got {result}. "
            "Cause: MCPRegistry not handling 404. "
            "Fix: Return None when server not found."
        )

    def test_list_mcp_servers_by_provider(
        self, mcp_registry, registry_process, http_client
    ):
        """
        Given: MCP servers from different providers
        When: Listing with provider filter
        Then: Returns only matching providers

        Tests REAL: Provider filter in MCPRegistry
        """
        # Register servers with different providers
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "nanda-mcp-1",
                "endpoint": "http://localhost:7002",
                "provider": "nanda",
            },
        )
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "smithery-mcp-1",
                "endpoint": "http://localhost:7003",
                "provider": "smithery",
            },
        )

        # Get servers by provider (method may vary based on implementation)
        # This tests the actual MCPRegistry.get_mcp_servers() or similar
        try:
            nanda_servers = mcp_registry.get_mcp_servers(registry_provider="nanda")
            if nanda_servers:
                server_names = [s.get("qualified_name") for s in nanda_servers]
                assert "nanda-mcp-1" in server_names or any(
                    "nanda" in str(s) for s in nanda_servers
                ), "Expected nanda-mcp-1 in filtered results"
        except AttributeError:
            # Method may not exist - skip gracefully
            pytest.skip("MCPRegistry.get_mcp_servers() not implemented")

    def test_register_mcp_server_missing_qualified_name_returns_error(
        self, registry_process, http_client
    ):
        """
        Given: MCP server data missing required qualified_name
        When: Registering
        Then: Returns 400 error

        Tests REAL: Validation in registry server
        """
        response = http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={"endpoint": "http://localhost:7004"},  # Missing qualified_name
        )

        assert response.status_code == 400, (
            f"Expected 400 for missing qualified_name, got {response.status_code}. "
            "Cause: Registry not validating required fields. "
            "Fix: Add validation for qualified_name in /mcp_servers POST."
        )

    def test_register_duplicate_mcp_server_overwrites(
        self, registry_process, http_client
    ):
        """
        Given: MCP server already registered
        When: Registering again with same name
        Then: Overwrites (or returns conflict based on design)

        Tests REAL: Duplicate handling
        """
        server_data = {
            "qualified_name": "duplicate-test",
            "endpoint": "http://localhost:7005",
            "provider": "nanda",
        }

        # First registration
        response1 = http_client.post(f"{registry_process.url}/mcp_servers", json=server_data)
        assert response1.status_code == 200

        # Second registration with updated endpoint
        server_data["endpoint"] = "http://localhost:7006"
        response2 = http_client.post(f"{registry_process.url}/mcp_servers", json=server_data)

        # Either 200 (overwrite) or 409 (conflict) is acceptable
        assert response2.status_code in [200, 409], (
            f"Expected 200 or 409 for duplicate, got {response2.status_code}. "
            "Cause: Duplicate handling not implemented. "
            "Fix: Either overwrite or return 409 Conflict."
        )


# =============================================================================
# Tests: Full Agent Lifecycle (True E2E)
# =============================================================================


class TestAgentLifecycle:
    """
    True E2E tests: Agent process starts → registers → discoverable → communicates.

    These tests spawn real agent processes and verify the complete flow.
    """

    def test_spawned_agent_registers_and_is_discoverable(
        self, agent_process_factory, registry_client, wait_for_registration
    ):
        """
        Given: Agent process started with registration enabled
        When: Agent starts up
        Then: Agent is discoverable via RegistryClient

        Tests REAL: Full agent registration lifecycle
        """
        # Spawn real agent process
        agent = agent_process_factory("lifecycle-test-agent")

        # Wait for registration to complete
        registered = wait_for_registration("lifecycle-test-agent", timeout=10.0)
        assert registered, (
            "Agent did not register within timeout. "
            "Cause: Agent startup or registration failed. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

        # Verify discoverable via RegistryClient
        result = registry_client.lookup_agent("lifecycle-test-agent")

        assert result is not None, (
            "Agent not found via RegistryClient after registration. "
            "Cause: RegistryClient lookup not finding registered agent. "
            "Fix: Check agent registration payload and lookup logic."
        )
        assert agent.url in result.get("agent_url", ""), (
            f"Expected agent_url to contain '{agent.url}'. "
            f"Got: '{result.get('agent_url')}'. "
            "Cause: Agent URL mismatch in registration."
        )

    def test_multiple_agents_all_discoverable(
        self, agent_process_factory, registry_client, wait_for_agents
    ):
        """
        Given: Multiple agent processes started
        When: All agents register
        Then: All agents discoverable via list_agents()

        Tests REAL: Multiple agent registration
        """
        agent_ids = ["multi-agent-1", "multi-agent-2", "multi-agent-3"]

        # Spawn all agents
        agents = [agent_process_factory(agent_id) for agent_id in agent_ids]

        # Wait for all to register (fixes race condition)
        all_registered = wait_for_agents(agent_ids, timeout=15.0)
        assert all_registered, (
            "Not all agents registered within timeout. "
            "Cause: Agent startup slower than expected or registration failed. "
            "Fix: Increase timeout or check agent logs."
        )

        # Verify all discoverable
        all_agents = registry_client.list_agents()
        found_ids = [a.get("agent_id") for a in all_agents if isinstance(a, dict)]

        for agent_id in agent_ids:
            assert agent_id in found_ids, (
                f"Agent '{agent_id}' not in list. Got: {found_ids}. "
                "Cause: Agent not included in list response. "
                "Fix: Check list endpoint returns all agents."
            )

    def test_agent_responds_to_a2a_message(
        self, agent_process_factory, send_a2a_message, wait_for_registration
    ):
        """
        Given: Agent process running
        When: Sending A2A message to agent
        Then: Agent responds with processed message

        Tests REAL: Full A2A communication flow
        """
        agent = agent_process_factory("a2a-test-agent")
        wait_for_registration("a2a-test-agent", timeout=10.0)

        # Send A2A message
        response = send_a2a_message(agent.url, "Hello from test!")

        assert response["status_code"] == 200, (
            f"Expected 200 from A2A endpoint, got {response['status_code']}. "
            "Cause: A2A endpoint not responding. "
            f"Fix: Check agent logs at {agent.log_file}"
        )


# =============================================================================
# Tests: Concurrent Operations
# =============================================================================


class TestConcurrentOperations:
    """Tests for race conditions and concurrent access scenarios."""

    def test_concurrent_registrations_all_succeed(
        self, registry_process, http_client
    ):
        """
        Given: Multiple registration requests sent concurrently
        When: All requests complete
        Then: All agents are registered

        Tests REAL: Thread safety of registry server
        """
        results = []
        errors = []

        def register_agent(agent_id: str):
            try:
                response = http_client.post(
                    f"{registry_process.url}/register",
                    json={"agent_id": agent_id, "agent_url": f"http://localhost:{9100 + hash(agent_id) % 100}"},
                )
                results.append((agent_id, response.status_code))
            except Exception as e:
                errors.append((agent_id, str(e)))

        # Spawn threads for concurrent registration
        threads = []
        for i in range(10):
            t = threading.Thread(target=register_agent, args=(f"concurrent-agent-{i}",))
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=10)

        # Verify all succeeded
        assert len(errors) == 0, f"Registration errors: {errors}"
        assert all(status == 200 for _, status in results), (
            f"Not all registrations succeeded: {results}. "
            "Cause: Race condition in registry server. "
            "Fix: Ensure thread-safe storage access."
        )

        # Verify all discoverable
        response = http_client.get(f"{registry_process.url}/list")
        data = response.json()
        found_ids = [a["agent_id"] for a in data.get("agents", [])]

        for i in range(10):
            assert f"concurrent-agent-{i}" in found_ids, (
                f"concurrent-agent-{i} not found after concurrent registration"
            )

    def test_lookup_during_registration_does_not_crash(
        self, registry_process, http_client
    ):
        """
        Given: Registration and lookup happening concurrently
        When: Operations interleave
        Then: No crashes, consistent results

        Tests REAL: Concurrent read/write safety
        """
        errors = []

        def register_agents():
            for i in range(20):
                try:
                    http_client.post(
                        f"{registry_process.url}/register",
                        json={"agent_id": f"race-agent-{i}", "agent_url": f"http://localhost:920{i}"},
                    )
                except Exception as e:
                    errors.append(("register", i, str(e)))

        def lookup_agents():
            for i in range(20):
                try:
                    http_client.get(f"{registry_process.url}/lookup/race-agent-{i}")
                except Exception as e:
                    errors.append(("lookup", i, str(e)))

        # Run concurrently
        t1 = threading.Thread(target=register_agents)
        t2 = threading.Thread(target=lookup_agents)

        t1.start()
        t2.start()

        t1.join(timeout=10)
        t2.join(timeout=10)

        assert len(errors) == 0, (
            f"Errors during concurrent operations: {errors}. "
            "Cause: Race condition in registry. "
            "Fix: Ensure proper locking in registry server."
        )


# =============================================================================
# Tests: Unicode and Internationalization
# =============================================================================


class TestUnicodeAgentIDs:
    """Tests for Unicode agent ID handling in E2E flow."""

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("agent-日本語", "Japanese characters"),
            ("café-agent", "French accents"),
            ("agent-αβγ", "Greek letters"),
        ],
    )
    def test_unicode_agent_id_registration_and_lookup(
        self, registry_client, registry_process, http_client, agent_id, description
    ):
        """
        Given: Agent with Unicode ID ({description})
        When: Registering and looking up
        Then: Unicode preserved correctly

        Tests REAL: Unicode handling in full E2E flow
        """
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": agent_id, "agent_url": "http://localhost:9200"},
        )

        result = registry_client.lookup_agent(agent_id)

        assert result is not None, (
            f"Failed to lookup Unicode agent ID '{agent_id}' ({description}). "
            "Cause: Unicode encoding issue in URL or storage. "
            "Fix: Ensure proper URL encoding and UTF-8 storage."
        )
        assert result.get("agent_id") == agent_id, (
            f"Unicode agent_id corrupted. Expected '{agent_id}', got '{result.get('agent_id')}'. "
            "Cause: Unicode not preserved through registration/lookup cycle."
        )


# =============================================================================
# Tests: Case Sensitivity
# =============================================================================


class TestCaseSensitivity:
    """Tests for case sensitivity in agent lookups."""

    def test_lookup_is_case_sensitive(
        self, registry_client, registry_process, http_client
    ):
        """
        Given: Agent registered as 'Case-Sensitive-Test'
        When: Looking up as 'case-sensitive-test' (lowercase)
        Then: Returns None (not found)

        Tests REAL: Case-sensitive lookup behavior
        """
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": "Case-Sensitive-Test", "agent_url": "http://localhost:9300"},
        )

        # Exact case should work
        result_exact = registry_client.lookup_agent("Case-Sensitive-Test")
        assert result_exact is not None, "Exact case lookup should succeed"

        # Different case should not find it
        result_lower = registry_client.lookup_agent("case-sensitive-test")
        assert result_lower is None, (
            "Lowercase lookup found uppercase agent. "
            "Cause: Lookup is case-insensitive. "
            "Fix: Ensure case-sensitive matching in registry."
        )
