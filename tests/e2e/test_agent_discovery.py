"""
E2E Tests for Agent Discovery.

Tests REAL registry lookup, search, and agent discovery operations
using actual HTTP requests to registry servers.

Test Categories:
- TestRegistryLookup: Agent lookup by ID
- TestRegistryList: Listing agents
- TestRegistrySearch: Search with filters
- TestRegistryStatus: Agent status operations
- TestRealRegistry: Tests against production registry.chat39.com
- TestMCPServerDiscovery: MCP server discovery operations
"""

import time

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Registry Lookup
# =============================================================================


class TestRegistryLookup:
    """Tests for agent lookup operations."""

    def test_lookup_registered_agent_returns_data(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: A registered agent
        When: Looking up by agent_id
        Then: Returns complete agent data

        Tests REAL: HTTP GET /lookup/{agent_id}
        Mocks: None
        """
        agent = agent_process_factory("lookup-test")

        response = http_client.get(f"{registry_process.url}/lookup/lookup-test")

        assert response.status_code == 200, (
            f"Expected 200 for registered agent lookup, got {response.status_code}. "
            f"Cause: Agent may not be registered. "
            f"Fix: Check registration in agent startup."
        )

        data = response.json()
        required_fields = ["agent_id", "agent_url"]
        for field in required_fields:
            assert field in data, (
                f"Expected '{field}' in lookup response. "
                f"Got keys: {list(data.keys())}. "
                f"Cause: Registration data incomplete. "
                f"Fix: Check NANDA._register() payload."
            )

        # Verify actual values match expected
        assert data["agent_id"] == "lookup-test", (
            f"Expected agent_id='lookup-test', got '{data['agent_id']}'. "
            f"Cause: Agent ID mismatch in registration. "
            f"Fix: Check agent_id passed to NANDA constructor."
        )
        assert agent.url in data["agent_url"], (
            f"Expected agent_url to contain '{agent.url}', got '{data['agent_url']}'. "
            f"Cause: Agent URL not registered correctly. "
            f"Fix: Check URL construction in NANDA._register()."
        )

    def test_lookup_unregistered_agent_returns_404(self, registry_process, http_client):
        """
        Given: An agent_id that doesn't exist
        When: Looking up in registry
        Then: Returns 404 Not Found

        Tests REAL: 404 handling for missing agents
        Mocks: None
        """
        response = http_client.get(
            f"{registry_process.url}/lookup/nonexistent-agent-xyz"
        )

        assert response.status_code == 404, (
            f"Expected 404 for nonexistent agent, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            f"Cause: Registry may be returning wrong status for missing agents. "
            f"Fix: Check /lookup endpoint 404 handling."
        )

    def test_lookup_case_sensitive(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Agent registered as 'Test-Agent'
        When: Looking up as 'test-agent' (lowercase)
        Then: Returns 404 (case sensitive)

        Tests REAL: Case sensitivity in lookup
        Mocks: None
        """
        agent = agent_process_factory("Case-Sensitive-Test")

        # Exact case should work
        response_exact = http_client.get(
            f"{registry_process.url}/lookup/Case-Sensitive-Test"
        )
        assert response_exact.status_code == 200, (
            f"Expected 200 for exact case lookup, got {response_exact.status_code}. "
            f"Cause: Case-Sensitive-Test agent may not be registered. "
            f"Fix: Check registration timing."
        )

        # Different case should fail
        response_lower = http_client.get(
            f"{registry_process.url}/lookup/case-sensitive-test"
        )
        assert response_lower.status_code == 404, (
            f"Expected 404 for different case, got {response_lower.status_code}. "
            f"Cause: Registry lookup may not be case-sensitive. "
            f"Fix: Ensure case-sensitive matching in registry."
        )

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("agent%20space", "URL-encoded space"),
            ("agent/slash", "forward slash"),
            ("agent?query", "question mark"),
        ],
    )
    def test_lookup_special_characters_in_url(
        self, registry_process, http_client, agent_id, description
    ):
        """
        Given: An agent_id with special URL characters ({description})
        When: Looking up in registry
        Then: Handles URL encoding correctly (404 or 400)

        Tests REAL: URL special character handling
        Mocks: None
        """
        import urllib.parse

        encoded_id = urllib.parse.quote(agent_id, safe="")

        response = http_client.get(f"{registry_process.url}/lookup/{encoded_id}")

        # Should return 404 (not found) or 400 (bad request), not 500
        assert response.status_code in [400, 404], (
            f"Expected 400/404 for special char lookup ({description}), got {response.status_code}. "
            f"Cause: Special characters not handled in URL. "
            f"Fix: Check URL decoding in /lookup endpoint."
        )


# =============================================================================
# Tests: Registry List
# =============================================================================


class TestRegistryList:
    """Tests for listing agents from registry."""

    def test_list_returns_all_registered_agents(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Multiple registered agents
        When: Calling /list endpoint
        Then: All agents are included in response

        Tests REAL: HTTP GET /list
        Mocks: None
        """
        agent_a = agent_process_factory("list-a")
        agent_b = agent_process_factory("list-b")
        agent_c = agent_process_factory("list-c")

        response = http_client.get(f"{registry_process.url}/list")

        assert response.status_code == 200, (
            f"Expected 200 from /list, got {response.status_code}. "
            f"Cause: List endpoint failed. "
            f"Fix: Check registry /list endpoint."
        )

        data = response.json()
        agent_ids = [a["agent_id"] for a in data["agents"]]

        for expected_id in ["list-a", "list-b", "list-c"]:
            assert expected_id in agent_ids, (
                f"Expected '{expected_id}' in agent list. "
                f"Got: {agent_ids}. "
                f"Cause: Agent not included in list. "
                f"Fix: Check list endpoint query."
            )

    def test_list_empty_registry_returns_empty_list(
        self, registry_process, http_client
    ):
        """
        Given: Empty registry (after reset)
        When: Calling /list endpoint
        Then: Returns empty agents list

        Tests REAL: Empty list handling
        Mocks: None
        """
        # Registry is reset by autouse fixture, so it's empty
        response = http_client.get(f"{registry_process.url}/list")

        assert response.status_code == 200, (
            f"Expected 200 from /list on empty registry, got {response.status_code}. "
            f"Cause: Empty registry handling issue. "
            f"Fix: Check empty list response."
        )

        data = response.json()
        assert data["count"] == 0, (
            f"Expected count=0 for empty registry, got {data['count']}. "
            f"Cause: Registry not empty after reset. "
            f"Fix: Check _reset endpoint."
        )

    def test_list_includes_count_field(
        self, registry_process, agent_process_factory, http_client
    ):
        """
        Given: Agents in registry
        When: Calling /list endpoint
        Then: Response includes accurate count field

        Tests REAL: Count field accuracy
        Mocks: None
        """
        agent_process_factory("count-test-1")
        agent_process_factory("count-test-2")

        response = http_client.get(f"{registry_process.url}/list")
        data = response.json()

        assert "count" in data, (
            f"Expected 'count' in response. "
            f"Got keys: {list(data.keys())}. "
            f"Cause: Count field missing. "
            f"Fix: Add count to /list response."
        )
        assert data["count"] == len(data["agents"]), (
            f"Count mismatch: count={data['count']}, agents={len(data['agents'])}. "
            f"Cause: Count calculation wrong. "
            f"Fix: Check count logic in /list."
        )


# =============================================================================
# Tests: Registry Search
# =============================================================================


class TestRegistrySearch:
    """Tests for searching agents with filters."""

    def test_search_by_query_matches_agent_id(
        self, registry_process, http_client, sample_agent_data
    ):
        """
        Given: Agent registered with specific name
        When: Searching with query matching agent_id
        Then: Returns matching agent

        Tests REAL: HTTP GET /search?q=...
        Mocks: None
        """
        # Register agent directly
        http_client.post(f"{registry_process.url}/register", json=sample_agent_data)

        response = http_client.get(f"{registry_process.url}/search?q=test-agent")

        assert response.status_code == 200, (
            f"Expected 200 from /search, got {response.status_code}. "
            f"Cause: Search endpoint failed. "
            f"Fix: Check /search endpoint."
        )

        data = response.json()
        agent_ids = [a["agent_id"] for a in data["agents"]]

        assert "test-agent" in agent_ids, (
            f"Expected 'test-agent' in search results. "
            f"Got: {agent_ids}. "
            f"Cause: Search query not matching agent_id. "
            f"Fix: Check query matching logic."
        )

    def test_search_by_capabilities(self, registry_process, http_client):
        """
        Given: Agent with specific capabilities
        When: Searching by capability
        Then: Returns matching agent

        Tests REAL: Capability filter
        Mocks: None
        """
        agent_data = {
            "agent_id": "capable-agent",
            "agent_url": "http://localhost:9999",
            "capabilities": ["data_analysis", "reporting"],
        }
        http_client.post(f"{registry_process.url}/register", json=agent_data)

        response = http_client.get(
            f"{registry_process.url}/search?capabilities=data_analysis"
        )
        data = response.json()

        agent_ids = [a["agent_id"] for a in data["agents"]]
        assert "capable-agent" in agent_ids, (
            f"Expected 'capable-agent' in capability search. "
            f"Got: {agent_ids}. "
            f"Cause: Capability filter not working. "
            f"Fix: Check capability matching in /search."
        )

    def test_search_by_tags(self, registry_process, http_client):
        """
        Given: Agent with specific tags
        When: Searching by tag
        Then: Returns matching agent

        Tests REAL: Tag filter
        Mocks: None
        """
        agent_data = {
            "agent_id": "tagged-agent",
            "agent_url": "http://localhost:9999",
            "tags": ["production", "ml"],
        }
        http_client.post(f"{registry_process.url}/register", json=agent_data)

        response = http_client.get(f"{registry_process.url}/search?tags=ml")
        data = response.json()

        agent_ids = [a["agent_id"] for a in data["agents"]]
        assert "tagged-agent" in agent_ids, (
            f"Expected 'tagged-agent' in tag search. "
            f"Got: {agent_ids}. "
            f"Cause: Tag filter not working. "
            f"Fix: Check tag matching in /search."
        )

    def test_search_no_matches_returns_empty(self, registry_process, http_client):
        """
        Given: No agents matching query
        When: Searching
        Then: Returns empty list

        Tests REAL: Empty search results
        Mocks: None
        """
        response = http_client.get(
            f"{registry_process.url}/search?q=nonexistent-xyz-123"
        )
        data = response.json()

        assert data["count"] == 0, (
            f"Expected 0 results for nonexistent query, got {data['count']}. "
            f"Cause: Search returning false positives. "
            f"Fix: Check search query logic."
        )


# =============================================================================
# Tests: Registry Status
# =============================================================================


class TestRegistryStatus:
    """Tests for agent status operations."""

    def test_update_agent_status(
        self, registry_process, http_client, sample_agent_data
    ):
        """
        Given: A registered agent
        When: Updating its status
        Then: Status is changed

        Tests REAL: HTTP PUT /status/{agent_id}
        Mocks: None
        """
        http_client.post(f"{registry_process.url}/register", json=sample_agent_data)

        # Update status
        response = http_client.put(
            f"{registry_process.url}/status/{sample_agent_data['agent_id']}",
            json={"status": "busy"},
        )

        assert response.status_code == 200, (
            f"Expected 200 from status update, got {response.status_code}. "
            f"Cause: Status update failed. "
            f"Fix: Check /status PUT endpoint."
        )

        # Verify status changed
        status_response = http_client.get(
            f"{registry_process.url}/status/{sample_agent_data['agent_id']}"
        )
        data = status_response.json()

        assert data.get("status") == "busy", (
            f"Expected status='busy', got '{data.get('status')}'. "
            f"Cause: Status not updated. "
            f"Fix: Check status storage."
        )

    def test_unregister_agent(self, registry_process, http_client, sample_agent_data):
        """
        Given: A registered agent
        When: Unregistering it
        Then: Agent is removed from registry

        Tests REAL: HTTP DELETE /unregister/{agent_id}
        Mocks: None
        """
        http_client.post(f"{registry_process.url}/register", json=sample_agent_data)

        # Verify registered
        lookup_before = http_client.get(
            f"{registry_process.url}/lookup/{sample_agent_data['agent_id']}"
        )
        assert lookup_before.status_code == 200, (
            f"Expected 200 before unregister, got {lookup_before.status_code}. "
            f"Cause: Agent was not registered properly. "
            f"Fix: Check /register endpoint."
        )

        # Unregister
        response = http_client.delete(
            f"{registry_process.url}/unregister/{sample_agent_data['agent_id']}"
        )

        assert response.status_code == 200, (
            f"Expected 200 from unregister, got {response.status_code}. "
            f"Cause: Unregister failed. "
            f"Fix: Check /unregister endpoint."
        )

        # Verify removed
        lookup_after = http_client.get(
            f"{registry_process.url}/lookup/{sample_agent_data['agent_id']}"
        )
        assert lookup_after.status_code == 404, (
            f"Expected 404 after unregister, got {lookup_after.status_code}. "
            f"Cause: Agent not removed. "
            f"Fix: Check deletion logic."
        )


# =============================================================================
# Tests: Real Registry (registry.chat39.com)
# =============================================================================


class TestRealRegistry:
    """Tests against the production registry.chat39.com."""

    def test_real_registry_health_check(
        self, real_registry_url, real_registry_available
    ):
        """
        Given: Production registry URL
        When: Calling health endpoint
        Then: Returns 200 (if available)

        Tests REAL: Production registry connectivity
        Mocks: None
        """
        if not real_registry_available:
            pytest.skip("Real registry not available")

        response = requests.get(
            f"{real_registry_url}/health", timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from real registry health, got {response.status_code}. "
            f"Cause: Production registry may be down. "
            f"Fix: Check registry.chat39.com status."
        )

    def test_real_registry_list_agents(
        self, real_registry_url, real_registry_available
    ):
        """
        Given: Production registry
        When: Listing agents
        Then: Returns valid response

        Tests REAL: Production registry list
        Mocks: None
        """
        if not real_registry_available:
            pytest.skip("Real registry not available")

        response = requests.get(
            f"{real_registry_url}/list", timeout=HTTP_REQUEST_TIMEOUT
        )

        # May return 200 or 404 depending on registry implementation
        assert response.status_code in [200, 404], (
            f"Expected 200/404 from real registry list, got {response.status_code}. "
            f"Cause: Unexpected response from production registry. "
            f"Fix: Check registry API documentation."
        )


# =============================================================================
# Tests: MCP Server Discovery
# =============================================================================


class TestMCPServerDiscovery:
    """Tests for MCP server discovery operations."""

    def test_register_mcp_server(
        self, registry_process, http_client, sample_mcp_server_data
    ):
        """
        Given: MCP server registration data
        When: Registering with registry
        Then: Server is stored and retrievable

        Tests REAL: HTTP POST /mcp_servers
        Mocks: None
        """
        response = http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        assert response.status_code == 200, (
            f"Expected 200 from MCP server registration, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            f"Cause: MCP server registration failed. "
            f"Fix: Check /mcp_servers POST endpoint."
        )

    def test_lookup_mcp_server(
        self, registry_process, http_client, sample_mcp_server_data
    ):
        """
        Given: A registered MCP server
        When: Looking up by qualified_name
        Then: Returns server data

        Tests REAL: HTTP GET /mcp_servers/{name}
        Mocks: None
        """
        http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        response = http_client.get(
            f"{registry_process.url}/mcp_servers/{sample_mcp_server_data['qualified_name']}"
        )

        assert response.status_code == 200, (
            f"Expected 200 for MCP server lookup, got {response.status_code}. "
            f"Cause: MCP server not found. "
            f"Fix: Check MCP server storage."
        )

        data = response.json()
        assert data["qualified_name"] == sample_mcp_server_data["qualified_name"], (
            f"Qualified name mismatch. "
            f"Expected: {sample_mcp_server_data['qualified_name']}. "
            f"Got: {data.get('qualified_name')}. "
            f"Cause: Data corruption in storage. "
            f"Fix: Check MCP server data handling."
        )

    def test_lookup_nonexistent_mcp_server(self, registry_process, http_client):
        """
        Given: Nonexistent MCP server name
        When: Looking up
        Then: Returns 404

        Tests REAL: 404 for missing MCP server
        Mocks: None
        """
        response = http_client.get(
            f"{registry_process.url}/mcp_servers/nonexistent-server-xyz"
        )

        assert response.status_code == 404, (
            f"Expected 404 for nonexistent MCP server, got {response.status_code}. "
            f"Cause: Wrong status for missing server. "
            f"Fix: Check /mcp_servers/{name} 404 handling."
        )

    def test_list_mcp_servers(
        self, registry_process, http_client, sample_mcp_server_data
    ):
        """
        Given: Registered MCP servers
        When: Listing servers
        Then: Returns all servers

        Tests REAL: HTTP GET /mcp_servers
        Mocks: None
        """
        http_client.post(
            f"{registry_process.url}/mcp_servers", json=sample_mcp_server_data
        )

        response = http_client.get(f"{registry_process.url}/mcp_servers")

        assert response.status_code == 200, (
            f"Expected 200 from MCP servers list, got {response.status_code}. "
            f"Cause: MCP servers list failed. "
            f"Fix: Check /mcp_servers GET endpoint."
        )

        data = response.json()
        assert "servers" in data, (
            f"Expected 'servers' in response. "
            f"Got keys: {list(data.keys())}. "
            f"Cause: Response format wrong. "
            f"Fix: Check list response format."
        )

    def test_list_mcp_servers_by_provider(self, registry_process, http_client):
        """
        Given: MCP servers from different providers
        When: Listing with provider filter
        Then: Returns only matching providers

        Tests REAL: Provider filter
        Mocks: None
        """
        # Register NANDA server
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "nanda-server-1",
                "endpoint": "http://localhost:7001",
                "provider": "nanda",
            },
        )

        # Register Smithery server
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "smithery-server-1",
                "endpoint": "http://localhost:7002",
                "provider": "smithery",
            },
        )

        # Filter by provider
        response = http_client.get(f"{registry_process.url}/mcp_servers?provider=nanda")
        data = response.json()

        server_names = [s["qualified_name"] for s in data["servers"]]
        assert (
            "nanda-server-1" in server_names
        ), "NANDA server should be in filtered results"
        assert "smithery-server-1" not in server_names, (
            "Smithery server should NOT be in nanda-filtered results. "
            f"Got: {server_names}. "
            f"Cause: Provider filter not working. "
            f"Fix: Check provider filter logic."
        )
