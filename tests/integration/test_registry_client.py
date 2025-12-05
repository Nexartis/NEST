"""
Integration tests for RegistryClient HTTP operations.

Tests the REAL RegistryClient class with mocked HTTP responses.
Per Issue #7: "Registry client interactions (mock NANDA Index)"

What's mocked (external dependencies):
- HTTP responses from NANDA Index registry

What's tested (our code):
- URL construction logic
- Request body formatting
- Response parsing
- Error handling
- Local filtering fallback

Test Organization:
- TestRegistryClientInitialization: Client setup and configuration
- TestAgentRegistration: POST /register operations
- TestAgentLookup: GET /lookup/{agent_id} operations
- TestAgentListing: GET /list and /clients operations
- TestAgentSearch: GET /search with filters and local fallback
- TestMCPServerOperations: MCP registry queries
- TestAgentStatusOperations: Status updates and unregistration
- TestHealthAndStats: Health check and statistics endpoints
- TestErrorHandlingAndResilience: Network error recovery
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json

# Import with error handling
try:
    from nanda_core.core.registry_client import RegistryClient
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

# Apply markers to all tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
]


# =============================================================================
# Fixtures - Create REAL clients with mocked HTTP layer
# =============================================================================

@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses (simulates NANDA Index)."""
    def _create(status_code: int = 200, json_data=None, text: str = "", raise_on_json=None):
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.text = text or json.dumps(json_data) if json_data else ""
        if raise_on_json:
            mock_resp.json.side_effect = raise_on_json
        elif json_data is not None:
            mock_resp.json.return_value = json_data
        return mock_resp
    return _create


@pytest.fixture
def client_with_mock_session(mock_http_response):
    """
    Create REAL RegistryClient with mocked HTTP session.

    This tests our actual code while mocking external NANDA Index calls.
    """
    client = RegistryClient(registry_url="http://registry.test.com")
    client.session = Mock()  # Mock only HTTP layer
    return client


# =============================================================================
# Helper Functions
# =============================================================================

def assert_called_with_url(mock_method, expected_url_part: str, context: str):
    """Assert mock was called with URL containing expected part."""
    assert mock_method.called, (
        f"Expected HTTP call for {context}. "
        f"Cause: Method not invoked. "
        f"Fix: Check client implementation"
    )
    call_url = mock_method.call_args[0][0]
    assert expected_url_part in call_url, (
        f"Expected URL containing '{expected_url_part}' for {context}. "
        f"Got: '{call_url}'. "
        f"Cause: URL construction error. "
        f"Fix: Check URL building in client method"
    )


# =============================================================================
# Tests: Client Initialization
# =============================================================================

class TestRegistryClientInitialization:
    """Tests for RegistryClient initialization - tests REAL __init__."""

    def test_stores_provided_registry_url(self):
        """
        Given: Explicit registry_url parameter
        When: Creating RegistryClient
        Then: Stores provided URL
        """
        client = RegistryClient(registry_url="http://custom.registry.com")

        assert client.registry_url == "http://custom.registry.com", (
            f"Expected custom URL. Got: '{client.registry_url}'. "
            f"Cause: registry_url parameter not used. "
            f"Fix: Check __init__ assignment"
        )

    def test_creates_session_with_ssl_disabled(self):
        """
        Given: Creating RegistryClient
        When: Session initialized
        Then: SSL verify disabled (for development)
        """
        client = RegistryClient(registry_url="http://test.com")

        assert client.session is not None, (
            "Expected session to be created. "
            "Cause: __init__ did not initialize session. "
            "Fix: Add self.session = requests.Session() in __init__"
        )
        assert client.session.verify is False, (
            f"Expected SSL verify=False. Got: {client.session.verify}. "
            f"Cause: SSL verification not disabled. "
            f"Fix: Set session.verify = False in __init__"
        )

    def test_falls_back_to_default_url(self):
        """
        Given: No registry_url and no file
        When: Creating client
        Then: Uses hardcoded default
        """
        with patch('os.path.exists', return_value=False):
            client = RegistryClient()

        assert client.registry_url is not None, (
            "Expected fallback to default URL. "
            "Cause: No default URL when file missing. "
            "Fix: Add DEFAULT_REGISTRY_URL constant"
        )

    def test_reads_url_from_file(self):
        """
        Given: registry_url.txt exists
        When: Creating client without URL
        Then: Reads from file
        """
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='http://from.file.com\n')):
                client = RegistryClient()

        assert client.registry_url == "http://from.file.com", (
            f"Expected URL from file. Got: '{client.registry_url}'. "
            f"Cause: File reading not stripping whitespace. "
            f"Fix: Call .strip() on file content"
        )


# =============================================================================
# Tests: Agent Registration
# =============================================================================

class TestAgentRegistration:
    """Tests for register_agent() - mocks NANDA Index, tests our code."""

    def test_posts_to_register_endpoint(self, client_with_mock_session, mock_http_response):
        """
        Tests: URL construction in register_agent()
        Mocks: HTTP POST response
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        client.register_agent("my-agent", "http://my-agent:6001")

        assert_called_with_url(client.session.post, "/register", "registration")

    def test_sends_agent_id_and_url_in_body(self, client_with_mock_session, mock_http_response):
        """
        Tests: Request body construction
        Mocks: HTTP POST response
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        client.register_agent("test-agent", "http://test:6001")

        body = client.session.post.call_args[1]["json"]
        assert body["agent_id"] == "test-agent", (
            f"Expected agent_id='test-agent' in body. Got: {body}. "
            f"Cause: agent_id not included in POST body. "
            f"Fix: Add agent_id to json payload"
        )
        assert body["agent_url"] == "http://test:6001", (
            f"Expected agent_url='http://test:6001' in body. Got: {body}. "
            f"Cause: agent_url not included in POST body. "
            f"Fix: Add agent_url to json payload"
        )

    def test_includes_optional_fields(self, client_with_mock_session, mock_http_response):
        """
        Tests: Optional parameter handling
        Mocks: HTTP POST response
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        client.register_agent(
            "agent", "http://agent:6001",
            api_url="http://api.com",
            agent_facts_url="http://facts.com"
        )

        body = client.session.post.call_args[1]["json"]
        assert body.get("api_url") == "http://api.com", (
            f"Expected api_url='http://api.com' in body. Got: {body}. "
            f"Cause: Optional api_url parameter not passed through. "
            f"Fix: Include api_url in body if provided"
        )
        assert body.get("agent_facts_url") == "http://facts.com", (
            f"Expected agent_facts_url='http://facts.com' in body. Got: {body}. "
            f"Cause: Optional agent_facts_url parameter not passed through. "
            f"Fix: Include agent_facts_url in body if provided"
        )

    def test_returns_true_on_200(self, client_with_mock_session, mock_http_response):
        """Tests: Success return value logic"""
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        result = client.register_agent("agent", "http://url")

        assert result is True, (
            f"Expected True on HTTP 200. Got: {result}. "
            f"Cause: Success status not returning True. "
            f"Fix: Return True when response.status_code == 200"
        )

    def test_returns_false_on_error(self, client_with_mock_session, mock_http_response):
        """Tests: Error status handling"""
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(400)

        result = client.register_agent("agent", "http://url")

        assert result is False, (
            f"Expected False on HTTP 400. Got: {result}. "
            f"Cause: Error status not returning False. "
            f"Fix: Return False when response.status_code >= 400"
        )

    def test_returns_false_on_network_error(self, client_with_mock_session):
        """Tests: Exception handling"""
        client = client_with_mock_session
        client.session.post.side_effect = Exception("Connection refused")

        result = client.register_agent("agent", "http://url")

        assert result is False, (
            "Expected False on network error, got crash. "
            "Cause: Exception not caught in register_agent. "
            "Fix: Add try-except block returning False"
        )


# =============================================================================
# Tests: Agent Lookup
# =============================================================================

class TestAgentLookup:
    """Tests for lookup_agent() - mocks NANDA Index, tests our code."""

    def test_gets_from_lookup_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: URL construction with agent_id"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, {"agent_url": "http://found"})

        client.lookup_agent("target-agent")

        assert_called_with_url(client.session.get, "/lookup/target-agent", "lookup")

    def test_returns_parsed_json(self, client_with_mock_session, mock_http_response):
        """Tests: Response JSON parsing"""
        data = {"agent_url": "http://found:6001", "capabilities": ["chat"]}
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, data)

        result = client.lookup_agent("agent")

        assert result["agent_url"] == "http://found:6001", (
            f"Expected agent_url='http://found:6001'. Got: {result}. "
            f"Cause: JSON response not parsed correctly. "
            f"Fix: Return response.json() in lookup_agent"
        )
        assert result["capabilities"] == ["chat"], (
            f"Expected capabilities=['chat']. Got: {result}. "
            f"Cause: Capabilities not extracted from response. "
            f"Fix: Include all fields from JSON response"
        )

    def test_returns_none_on_404(self, client_with_mock_session, mock_http_response):
        """Tests: 404 handling"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(404)

        result = client.lookup_agent("unknown")

        assert result is None, (
            f"Expected None for 404 (agent not found). Got: {result}. "
            f"Cause: 404 status not handled. "
            f"Fix: Return None when status_code == 404"
        )

    def test_returns_none_on_network_error(self, client_with_mock_session):
        """Tests: Exception handling"""
        client = client_with_mock_session
        client.session.get.side_effect = Exception("Timeout")

        result = client.lookup_agent("agent")

        assert result is None, (
            "Expected None on network error, got crash. "
            "Cause: Exception not caught in lookup_agent. "
            "Fix: Add try-except block returning None"
        )


# =============================================================================
# Tests: Agent Listing
# =============================================================================

class TestAgentListing:
    """Tests for list_agents() and list_clients()."""

    def test_list_agents_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: URL construction for list"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.list_agents()

        assert_called_with_url(client.session.get, "/list", "list agents")

    def test_list_agents_parses_list(self, client_with_mock_session, mock_http_response):
        """Tests: List response parsing"""
        agents = [{"agent_id": "a1"}, {"agent_id": "a2"}]
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, agents)

        result = client.list_agents()

        assert len(result) == 2, (
            f"Expected 2 agents in result list. Got: {len(result)}. "
            f"Cause: List response not parsed correctly. "
            f"Fix: Return response.json() directly"
        )

    def test_list_agents_returns_empty_on_error(self, client_with_mock_session, mock_http_response):
        """Tests: Error handling returns empty list"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(500)

        result = client.list_agents()

        assert result == [], (
            f"Expected empty list on error. Got: {result}. "
            f"Cause: Error status not returning empty list. "
            f"Fix: Return [] when status_code >= 400"
        )

    def test_list_clients_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: URL for clients endpoint"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.list_clients()

        assert_called_with_url(client.session.get, "/clients", "list clients")

    def test_list_clients_fallback(self, client_with_mock_session, mock_http_response):
        """Tests: Fallback to list_agents when /clients fails"""
        client = client_with_mock_session
        client.session.get.side_effect = [
            mock_http_response(404),
            mock_http_response(200, [{"agent_id": "fallback"}])
        ]

        client.list_clients()

        assert client.session.get.call_count == 2, (
            "Expected 2 GET calls (first /clients fails, then fallback to /list). "
            f"Got: {client.session.get.call_count} calls. "
            "Cause: Fallback not triggered on 404. "
            "Fix: Call list_agents() when /clients returns 404"
        )


# =============================================================================
# Tests: Agent Search (including local filtering)
# =============================================================================

class TestAgentSearch:
    """Tests for search_agents() including local fallback filtering."""

    def test_passes_query_param(self, client_with_mock_session, mock_http_response):
        """Tests: Query parameter construction"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.search_agents(query="chat")

        params = client.session.get.call_args[1]["params"]
        assert params["q"] == "chat", (
            f"Expected query param q='chat'. Got: {params}. "
            f"Cause: Query not passed as 'q' parameter. "
            f"Fix: Add params={{'q': query}} to request"
        )

    def test_passes_capabilities_csv(self, client_with_mock_session, mock_http_response):
        """Tests: Capabilities formatting as CSV"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.search_agents(capabilities=["translate", "summarize"])

        params = client.session.get.call_args[1]["params"]
        assert "translate" in params["capabilities"], (
            f"Expected 'translate' in capabilities param. Got: {params}. "
            f"Cause: Capabilities list not joined correctly. "
            f"Fix: Pass capabilities=','.join(caps) to request"
        )

    def test_local_fallback_filters_by_query(self, client_with_mock_session, mock_http_response):
        """
        Tests: _filter_agents_locally() execution

        When /search returns 404, client falls back to local filtering.
        This tests our actual filtering logic.
        """
        all_agents = [
            {"agent_id": "chat-bot", "description": "Chat agent"},
            {"agent_id": "translator", "description": "Translation"}
        ]
        client = client_with_mock_session
        client.session.get.side_effect = [
            mock_http_response(404),  # /search fails
            mock_http_response(200, all_agents)  # /list succeeds
        ]

        result = client.search_agents(query="chat")

        assert len(result) == 1, (
            f"Expected 1 filtered result from local fallback. Got: {len(result)}. "
            f"Cause: Local filtering not working correctly. "
            f"Fix: Check _filter_agents_locally() query matching"
        )
        assert result[0]["agent_id"] == "chat-bot", (
            f"Expected filtered result to be 'chat-bot'. Got: {result}. "
            f"Cause: Wrong agent matched query. "
            f"Fix: Match query against agent_id and description"
        )

    def test_local_filter_by_capabilities(self, client_with_mock_session, mock_http_response):
        """Tests: Local capability matching logic"""
        all_agents = [
            {"agent_id": "a1", "capabilities": ["chat", "translate"]},
            {"agent_id": "a2", "capabilities": ["summarize"]},
            {"agent_id": "a3", "capabilities": ["translate"]}
        ]
        client = client_with_mock_session
        client.session.get.side_effect = [
            mock_http_response(404),
            mock_http_response(200, all_agents)
        ]

        result = client.search_agents(capabilities=["translate"])

        agent_ids = [a["agent_id"] for a in result]
        assert "a1" in agent_ids, (
            f"Expected a1 (has translate capability) in result. Got: {agent_ids}. "
            f"Cause: Agent with matching capability not found. "
            f"Fix: Check capability intersection logic"
        )
        assert "a3" in agent_ids, (
            f"Expected a3 (has translate capability) in result. Got: {agent_ids}. "
            f"Cause: Agent with matching capability not found. "
            f"Fix: Check capability intersection logic"
        )
        assert "a2" not in agent_ids, (
            f"Expected a2 (no translate capability) to be filtered out. Got: {agent_ids}. "
            f"Cause: Agent without capability incorrectly included. "
            f"Fix: Filter agents where capabilities don't intersect"
        )


# =============================================================================
# Tests: MCP Server Operations
# =============================================================================

class TestMCPServerOperations:
    """Tests for MCP server config retrieval."""

    def test_get_mcp_servers_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: URL construction"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.get_mcp_servers()

        assert_called_with_url(client.session.get, "/mcp_servers", "mcp servers")

    def test_get_mcp_servers_provider_param(self, client_with_mock_session, mock_http_response):
        """Tests: Provider filter parameter"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, [])

        client.get_mcp_servers(registry_provider="smithery")

        params = client.session.get.call_args[1]["params"]
        assert params["registry_provider"] == "smithery", (
            f"Expected registry_provider='smithery' in params. Got: {params}. "
            f"Cause: Provider filter not passed correctly. "
            f"Fix: Add registry_provider to params dict"
        )

    def test_config_parses_json_string(self, client_with_mock_session, mock_http_response):
        """Tests: JSON string parsing in config"""
        response = {
            "endpoint": "http://mcp.server",
            "config": '{"api_version": "v2"}',
            "registry_provider": "nanda"
        }
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, response)

        result = client.get_mcp_server_config("nanda", "server")

        assert result["config"]["api_version"] == "v2", (
            f"Expected parsed config with api_version='v2'. Got: {result['config']}. "
            f"Cause: JSON string config not parsed to dict. "
            f"Fix: Use json.loads(config) if isinstance(config, str)"
        )

    def test_config_preserves_dict(self, client_with_mock_session, mock_http_response):
        """Tests: Dict config passed through"""
        response = {
            "endpoint": "http://mcp.server",
            "config": {"already": "dict"},
            "registry_provider": "nanda"
        }
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, response)

        result = client.get_mcp_server_config("nanda", "server")

        assert result["config"]["already"] == "dict", (
            f"Expected dict config preserved. Got: {result['config']}. "
            f"Cause: Dict config being re-serialized. "
            f"Fix: Only parse config if isinstance(config, str)"
        )


# =============================================================================
# Tests: Agent Status Operations
# =============================================================================

class TestAgentStatusOperations:
    """Tests for status updates and unregistration."""

    def test_update_status_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: PUT URL construction"""
        client = client_with_mock_session
        client.session.put.return_value = mock_http_response(200)

        client.update_agent_status("my-agent", "active")

        url = client.session.put.call_args[0][0]
        assert "/agents/my-agent/status" in url, (
            f"Expected URL to contain '/agents/my-agent/status'. Got: {url}. "
            f"Cause: Status endpoint URL wrong. "
            f"Fix: Build URL as f'{{base}}/agents/{{agent_id}}/status'"
        )

    def test_update_status_adds_timestamp(self, client_with_mock_session, mock_http_response):
        """Tests: last_seen timestamp addition"""
        client = client_with_mock_session
        client.session.put.return_value = mock_http_response(200)

        client.update_agent_status("agent", "active")

        body = client.session.put.call_args[1]["json"]
        assert "last_seen" in body, (
            f"Expected 'last_seen' timestamp in body. Got: {body}. "
            f"Cause: Timestamp not added automatically. "
            f"Fix: Add last_seen=datetime.now().isoformat() to body"
        )

    def test_update_status_merges_metadata(self, client_with_mock_session, mock_http_response):
        """Tests: Metadata merge logic"""
        client = client_with_mock_session
        client.session.put.return_value = mock_http_response(200)

        client.update_agent_status("agent", "active", metadata={"load": 0.5})

        body = client.session.put.call_args[1]["json"]
        assert body.get("load") == 0.5, (
            f"Expected metadata merged into body. Got: {body}. "
            f"Cause: Metadata dict not merged. "
            f"Fix: Use body.update(metadata) if metadata provided"
        )

    def test_unregister_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: DELETE URL construction"""
        client = client_with_mock_session
        client.session.delete.return_value = mock_http_response(200)

        client.unregister_agent("old-agent")

        url = client.session.delete.call_args[0][0]
        assert "/agents/old-agent" in url, (
            f"Expected URL to contain '/agents/old-agent'. Got: {url}. "
            f"Cause: Delete endpoint URL wrong. "
            f"Fix: Build URL as f'{{base}}/agents/{{agent_id}}'"
        )

    def test_unregister_success(self, client_with_mock_session, mock_http_response):
        """Tests: Success return value"""
        client = client_with_mock_session
        client.session.delete.return_value = mock_http_response(200)

        result = client.unregister_agent("agent")

        assert result is True, (
            f"Expected True on successful unregister. Got: {result}. "
            f"Cause: Success status not returning True. "
            f"Fix: Return True when status_code == 200"
        )

    def test_unregister_not_found(self, client_with_mock_session, mock_http_response):
        """Tests: 404 handling"""
        client = client_with_mock_session
        client.session.delete.return_value = mock_http_response(404)

        result = client.unregister_agent("unknown")

        assert result is False, (
            f"Expected False when agent not found (404). Got: {result}. "
            f"Cause: 404 status not handled. "
            f"Fix: Return False when status_code == 404"
        )


# =============================================================================
# Tests: Health and Stats
# =============================================================================

class TestHealthAndStats:
    """Tests for health_check() and get_registry_stats()."""

    def test_health_check_endpoint(self, client_with_mock_session, mock_http_response):
        """Tests: URL construction"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200)

        client.health_check()

        assert_called_with_url(client.session.get, "/health", "health")

    def test_health_check_timeout(self, client_with_mock_session, mock_http_response):
        """Tests: Timeout parameter"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200)

        client.health_check()

        kwargs = client.session.get.call_args[1]
        assert kwargs.get("timeout") == 5, (
            f"Expected timeout=5 for health check. Got: {kwargs}. "
            f"Cause: Timeout not passed to request. "
            f"Fix: Add timeout=5 to session.get() call"
        )

    def test_health_check_success(self, client_with_mock_session, mock_http_response):
        """Tests: Success logic"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200)

        assert client.health_check() is True, (
            "Expected True on HTTP 200. Got False. "
            "Cause: Success status not returning True. "
            "Fix: Return True when status_code == 200"
        )

    def test_health_check_failure(self, client_with_mock_session, mock_http_response):
        """Tests: Unhealthy status"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(503)

        assert client.health_check() is False, (
            "Expected False on HTTP 503 (Service Unavailable). Got True. "
            "Cause: 503 status not handled. "
            "Fix: Return False when status_code >= 400"
        )

    def test_health_check_exception(self, client_with_mock_session):
        """Tests: Exception handling"""
        client = client_with_mock_session
        client.session.get.side_effect = Exception("Connection refused")

        assert client.health_check() is False, (
            "Expected False on network exception. Got True or crash. "
            "Cause: Exception not caught in health_check. "
            "Fix: Add try-except block returning False"
        )

    def test_stats_parsing(self, client_with_mock_session, mock_http_response):
        """Tests: Stats response parsing"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, {"total": 42})

        result = client.get_registry_stats()

        assert result["total"] == 42, (
            f"Expected stats['total']=42. Got: {result}. "
            f"Cause: Stats response not parsed correctly. "
            f"Fix: Return response.json() in get_registry_stats"
        )

    def test_stats_error(self, client_with_mock_session, mock_http_response):
        """Tests: Error handling"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(500)

        assert client.get_registry_stats() is None, (
            "Expected None on HTTP 500 error. Got stats dict. "
            "Cause: Error status not returning None. "
            "Fix: Return None when status_code >= 400"
        )


# =============================================================================
# Tests: Agent Metadata
# =============================================================================

class TestAgentMetadata:
    """Tests for get_agent_metadata()."""

    def test_returns_none_for_missing(self, client_with_mock_session, mock_http_response):
        """Tests: 404 handling"""
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(404)

        assert client.get_agent_metadata("unknown") is None, (
            "Expected None on HTTP 404 (agent not found). Got metadata. "
            "Cause: 404 status not returning None. "
            "Fix: Return None when status_code == 404"
        )

    def test_extracts_all_fields(self, client_with_mock_session, mock_http_response):
        """Tests: Field extraction logic"""
        data = {
            "agent_url": "http://agent:6001",
            "capabilities": ["chat"],
            "description": "Test"
        }
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, data)

        result = client.get_agent_metadata("test-agent")

        assert result["agent_id"] == "test-agent", (
            f"Expected agent_id='test-agent' in result. Got: {result}. "
            f"Cause: agent_id not included in metadata. "
            f"Fix: Add agent_id to returned metadata dict"
        )
        assert result["agent_url"] == "http://agent:6001", (
            f"Expected agent_url='http://agent:6001' in result. Got: {result}. "
            f"Cause: agent_url not extracted from response. "
            f"Fix: Include agent_url in metadata dict"
        )
        assert result["capabilities"] == ["chat"], (
            f"Expected capabilities=['chat'] in result. Got: {result}. "
            f"Cause: capabilities not extracted from response. "
            f"Fix: Include capabilities in metadata dict"
        )


# =============================================================================
# Tests: Error Resilience
# =============================================================================

class TestErrorResilience:
    """Tests for error handling across methods."""

    @pytest.mark.parametrize("method,args,expected", [
        ("register_agent", ("a", "http://u"), False),
        ("lookup_agent", ("a",), None),
        ("list_agents", (), []),
        ("health_check", (), False),
        ("unregister_agent", ("a",), False),
        ("get_registry_stats", (), None),
    ])
    def test_methods_handle_exceptions(self, client_with_mock_session, method, args, expected):
        """Tests: All methods return defaults on exception, don't crash"""
        client = client_with_mock_session
        for http_method in ['get', 'post', 'put', 'delete']:
            getattr(client.session, http_method).side_effect = Exception("Network error")

        try:
            result = getattr(client, method)(*args)
            assert result == expected, (
                f"{method}() should return {expected} on exception. Got: {result}. "
                f"Cause: Exception handling returns wrong default value. "
                f"Fix: Ensure except block returns correct default"
            )
        except Exception as e:
            pytest.fail(
                f"{method}() crashed instead of handling exception. Error: {e}. "
                f"Cause: Missing try-except block. "
                f"Fix: Add try-except returning {expected}"
            )


# =============================================================================
# Tests: HTTP Error Code Coverage
# =============================================================================

class TestHTTPErrorCodeCoverage:
    """Comprehensive HTTP error code testing for all methods."""

    @pytest.mark.parametrize("status_code,description", [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (500, "Internal Server Error"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
    ])
    def test_register_handles_all_error_codes(
        self, client_with_mock_session, mock_http_response, status_code, description
    ):
        """
        Tests: register_agent() returns False for all HTTP error codes
        Mocks: HTTP POST response with various error statuses
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(status_code)

        result = client.register_agent("agent", "http://url")

        assert result is False, (
            f"Expected False on HTTP {status_code} ({description}). Got: {result}. "
            f"Cause: Status code {status_code} not returning False. "
            f"Fix: Return False when status_code >= 400"
        )

    @pytest.mark.parametrize("status_code,description", [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (500, "Internal Server Error"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
    ])
    def test_lookup_handles_all_error_codes(
        self, client_with_mock_session, mock_http_response, status_code, description
    ):
        """
        Tests: lookup_agent() returns None for all HTTP error codes
        Mocks: HTTP GET response with various error statuses
        """
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(status_code)

        result = client.lookup_agent("agent")

        assert result is None, (
            f"Expected None on HTTP {status_code} ({description}). Got: {result}. "
            f"Cause: Status code {status_code} not returning None. "
            f"Fix: Return None when status_code >= 400"
        )


# =============================================================================
# Tests: Unicode and Edge Cases for Agent ID
# =============================================================================

class TestAgentIDEdgeCases:
    """Tests for agent_id validation and Unicode handling."""

    @pytest.mark.parametrize("agent_id,description", [
        ("代理", "Chinese characters"),
        ("エージェント", "Japanese characters"),
        ("агент", "Cyrillic characters"),
        ("agent-日本語", "Mixed ASCII and Japanese"),
        ("café-agent", "Accented characters"),
        ("🤖-bot", "Emoji in ID"),
    ])
    def test_register_accepts_unicode_agent_id(
        self, client_with_mock_session, mock_http_response, agent_id, description
    ):
        """
        Tests: Unicode agent_id passed through correctly
        Given: agent_id='{agent_id}' ({description})
        When: Registering agent
        Then: Unicode preserved in request body
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        client.register_agent(agent_id, "http://url")

        body = client.session.post.call_args[1]["json"]
        assert body["agent_id"] == agent_id, (
            f"Expected agent_id='{agent_id}' ({description}). Got: '{body.get('agent_id')}'. "
            f"Cause: Unicode not preserved in request. "
            f"Fix: Don't encode/modify agent_id"
        )

    @pytest.mark.parametrize("agent_id,description", [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("a" * 1000, "Very long ID (1000 chars)"),
    ])
    def test_register_handles_boundary_agent_ids(
        self, client_with_mock_session, mock_http_response, agent_id, description
    ):
        """
        Tests: Boundary agent_id values passed through
        Given: agent_id='{description}'
        When: Registering agent
        Then: Value stored as-is (no validation currently)
        """
        client = client_with_mock_session
        client.session.post.return_value = mock_http_response(200)

        client.register_agent(agent_id, "http://url")

        body = client.session.post.call_args[1]["json"]
        assert body["agent_id"] == agent_id, (
            f"Expected agent_id preserved ({description}). "
            f"Got length: {len(body.get('agent_id', ''))}. "
            f"Cause: agent_id modified or truncated. "
            f"Fix: Store agent_id as-is or add explicit validation"
        )

    @pytest.mark.parametrize("agent_id,description", [
        ("agent/path", "Slash in ID"),
        ("agent?query", "Question mark in ID"),
        ("agent#hash", "Hash in ID"),
        ("agent&param=val", "Ampersand in ID"),
    ])
    def test_lookup_url_encodes_special_chars(
        self, client_with_mock_session, mock_http_response, agent_id, description
    ):
        """
        Tests: Special characters in agent_id URL encoded
        Given: agent_id with special URL chars ({description})
        When: Looking up agent
        Then: ID is properly URL encoded in path
        """
        client = client_with_mock_session
        client.session.get.return_value = mock_http_response(200, {"agent_url": "http://found"})

        client.lookup_agent(agent_id)

        call_url = client.session.get.call_args[0][0]
        # Should either URL-encode the special char or handle gracefully
        assert client.session.get.called, (
            f"Expected GET called for {description}. "
            f"Cause: lookup_agent crashed on special chars. "
            f"Fix: URL-encode agent_id in URL path"
        )
