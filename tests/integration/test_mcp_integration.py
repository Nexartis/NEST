"""
Integration tests for MCP (Model Context Protocol) client and registry.

Tests the MCP subsystem which handles:
- MCP server discovery from NANDA and Smithery registries
- Server URL construction with authentication
- Server connection (SSE and HTTP transports)
- Query execution and response parsing

All tests mock external HTTP and MCP server connections.

Test Organization:
- TestMCPRegistryInitialization: Registry setup and configuration
- TestNANDAMCPServerLookup: NANDA registry server discovery
- TestSmitheryMCPServerLookup: Smithery registry API integration
- TestServerURLConstruction: URL building with auth tokens
- TestMCPClientResultParsing: JSON-RPC response parsing
- TestMCPRegistryEdgeCases: Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
import base64

# Import with error handling - separate imports for graceful degradation
REGISTRY_IMPORT_SUCCESS = False
CLIENT_IMPORT_SUCCESS = False
IMPORT_ERROR = None

try:
    from nanda_core.core.mcp_registry import MCPRegistry
    REGISTRY_IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_ERROR = str(e)

# Mock missing mcp.client.streamable_http before importing MCPClient
import sys
from unittest.mock import MagicMock

# Create mock for missing streamable_http module (not in mcp 1.6.0)
if 'mcp.client.streamable_http' not in sys.modules:
    mock_streamable = MagicMock()
    mock_streamable.streamablehttp_client = MagicMock()
    sys.modules['mcp.client.streamable_http'] = mock_streamable

try:
    from nanda_core.core.mcp_client import MCPClient
    CLIENT_IMPORT_SUCCESS = True
except ImportError as e:
    # MCPClient may have other optional dependencies
    CLIENT_IMPORT_SUCCESS = False
    if not IMPORT_ERROR:
        IMPORT_ERROR = str(e)

# Apply markers to all tests
pytestmark = [
    pytest.mark.integration,
]

# Skip decorators for specific imports
skip_if_no_registry = pytest.mark.skipif(
    not REGISTRY_IMPORT_SUCCESS,
    reason=f"MCPRegistry import failed: {IMPORT_ERROR}"
)
skip_if_no_client = pytest.mark.skipif(
    not CLIENT_IMPORT_SUCCESS,
    reason=f"MCPClient import failed (optional mcp dependency)"
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mcp_registry():
    """MCPRegistry with test URLs."""
    return MCPRegistry(
        mcp_registry_url="http://mcp.registry.test",
        agent_registry_url="http://agent.registry.test"
    )


@pytest.fixture
def mcp_registry_with_smithery_key():
    """MCPRegistry with Smithery API key set."""
    with patch.dict('os.environ', {'SMITHERY_API_KEY': 'test-smithery-key-12345'}):
        registry = MCPRegistry(
            mcp_registry_url="http://mcp.registry.test",
            agent_registry_url="http://agent.registry.test"
        )
        yield registry


@pytest.fixture
def mcp_client():
    """MCPClient instance for testing."""
    return MCPClient()


@pytest.fixture
def mock_http_response():
    """Factory for creating mock HTTP responses."""
    def _create(status_code: int = 200, json_data=None, raise_exception=None):
        mock_resp = Mock()
        mock_resp.status_code = status_code
        mock_resp.text = json.dumps(json_data) if json_data else ""
        if json_data is not None:
            mock_resp.json.return_value = json_data
        if raise_exception:
            mock_resp.json.side_effect = raise_exception
        return mock_resp
    return _create


# =============================================================================
# Helper Functions
# =============================================================================

def assert_contains_all(result: dict, required_keys: list, context: str):
    """Assert result dict contains all required keys."""
    for key in required_keys:
        assert key in result, (
            f"Expected '{key}' in {context} result. "
            f"Got keys: {list(result.keys())}. "
            f"Fix: Ensure {key} is returned from lookup"
        )


# =============================================================================
# Tests: MCP Registry Initialization
# =============================================================================

@skip_if_no_registry
class TestMCPRegistryInitialization:
    """Tests for MCPRegistry initialization and configuration."""

    def test_stores_mcp_registry_url(self):
        """
        Given: MCP registry URL
        When: Creating MCPRegistry
        Then: Stores URL for lookups
        """
        registry = MCPRegistry(mcp_registry_url="http://custom.mcp.registry")

        assert registry.mcp_registry_url == "http://custom.mcp.registry", (
            f"Expected custom MCP registry URL. "
            f"Got: '{registry.mcp_registry_url}'. "
            f"Cause: mcp_registry_url parameter not stored. "
            f"Fix: Add self.mcp_registry_url = mcp_registry_url in __init__"
        )

    def test_stores_agent_registry_url(self):
        """
        Given: Agent registry URL
        When: Creating MCPRegistry
        Then: Stores URL for agent registry queries
        """
        registry = MCPRegistry(
            mcp_registry_url="http://mcp.test",
            agent_registry_url="http://custom.agent.registry"
        )

        assert registry.agent_registry_url == "http://custom.agent.registry", (
            f"Expected custom agent registry URL. "
            f"Got: '{registry.agent_registry_url}'. "
            f"Cause: agent_registry_url parameter not stored. "
            f"Fix: Add self.agent_registry_url = agent_registry_url in __init__"
        )

    def test_uses_default_agent_registry_url(self):
        """
        Given: No agent_registry_url provided
        When: Creating MCPRegistry
        Then: Uses default URL
        """
        registry = MCPRegistry(mcp_registry_url="http://mcp.test")

        assert registry.agent_registry_url is not None, (
            "Expected default agent registry URL. Got None. "
            "Cause: No default value set for agent_registry_url. "
            "Fix: Add DEFAULT_AGENT_REGISTRY_URL constant and use as fallback"
        )

    def test_reads_smithery_api_key_from_env(self):
        """
        Given: SMITHERY_API_KEY in environment
        When: Creating MCPRegistry
        Then: Stores API key for Smithery lookups
        """
        with patch.dict('os.environ', {'SMITHERY_API_KEY': 'my-secret-key'}):
            registry = MCPRegistry(mcp_registry_url="http://mcp.test")

        assert registry.smithery_api_key == "my-secret-key", (
            f"Expected Smithery key from env. "
            f"Got: '{registry.smithery_api_key}'. "
            f"Cause: SMITHERY_API_KEY not read from os.environ. "
            f"Fix: Add self.smithery_api_key = os.environ.get('SMITHERY_API_KEY') in __init__"
        )


# =============================================================================
# Tests: NANDA MCP Server Lookup
# =============================================================================

@skip_if_no_registry
class TestNANDAMCPServerLookup:
    """Tests for NANDA registry MCP server discovery."""

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_lookup_calls_nanda_endpoint(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Server name to look up
        When: Calling get_nanda_mcp_server_info()
        Then: Queries /mcp_servers/{server_name}
        """
        mock_get.return_value = mock_http_response(200, {
            "server_url": "http://server.test",
            "description": "Test server"
        })

        mcp_registry.get_nanda_mcp_server_info("my-server")

        call_url = mock_get.call_args[0][0]
        assert "/mcp_servers/my-server" in call_url, (
            f"Expected /mcp_servers/my-server endpoint. "
            f"Got: '{call_url}'. "
            f"Cause: URL construction incorrect. "
            f"Fix: Use f'{{mcp_registry_url}}/mcp_servers/{{server_name}}'"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_lookup_returns_server_info_on_success(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Server exists in NANDA registry
        When: Looking up
        Then: Returns server info dict with required fields
        """
        mock_get.return_value = mock_http_response(200, {
            "server_url": "http://found.server:8080",
            "description": "MCP Test Server",
            "config": {"key": "value"}
        })

        result = mcp_registry.get_nanda_mcp_server_info("test-server")

        assert result is not None, (
            "Expected server info dict. Got None. "
            "Cause: Success response not parsed. "
            "Fix: Return response.json() on status 200"
        )
        assert_contains_all(result, ["server_name", "server_url", "registry_provider"], "NANDA lookup")
        assert result["server_url"] == "http://found.server:8080", (
            f"Expected server_url from response. Got: '{result.get('server_url')}'. "
            f"Cause: server_url field not extracted. "
            f"Fix: Include server_url in returned dict"
        )
        assert result["registry_provider"] == "nanda", (
            f"Expected registry_provider='nanda'. Got: '{result.get('registry_provider')}'. "
            f"Cause: registry_provider not set. "
            f"Fix: Add registry_provider='nanda' to result dict"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_lookup_returns_none_on_404(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Server not in NANDA registry
        When: Looking up
        Then: Returns None
        """
        mock_get.return_value = mock_http_response(404)

        result = mcp_registry.get_nanda_mcp_server_info("unknown-server")

        assert result is None, (
            f"Expected None for 404 (server not found). Got: {result}. "
            f"Cause: 404 status not handled. "
            f"Fix: Return None when response.status_code == 404"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_lookup_handles_network_error(self, mock_get, mcp_registry):
        """
        Given: Network error during lookup
        When: Looking up
        Then: Returns None (not crash)
        """
        mock_get.side_effect = Exception("Connection timeout")

        result = mcp_registry.get_nanda_mcp_server_info("server")

        assert result is None, (
            "Expected None on network error. Got crash. "
            "Fix: Wrap request in try-except"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_lookup_handles_endpoint_field(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Response uses 'endpoint' instead of 'server_url'
        When: Looking up
        Then: Extracts URL from 'endpoint' field

        Why: Different registries may use different field names.
        """
        mock_get.return_value = mock_http_response(200, {
            "endpoint": "http://alt.endpoint:9000"
        })

        result = mcp_registry.get_nanda_mcp_server_info("server")

        assert result is not None, (
            "Expected result for endpoint field. Got None. "
            "Cause: 'endpoint' field not recognized. "
            "Fix: Check for both 'server_url' and 'endpoint' keys"
        )
        assert result["server_url"] == "http://alt.endpoint:9000", (
            f"Expected server_url from 'endpoint' field. "
            f"Got: '{result.get('server_url')}'. "
            f"Cause: 'endpoint' field not mapped to server_url. "
            f"Fix: Map response['endpoint'] to result['server_url']"
        )


# =============================================================================
# Tests: Smithery MCP Server Lookup
# =============================================================================

@skip_if_no_registry
class TestSmitheryMCPServerLookup:
    """Tests for Smithery registry API integration."""

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_smithery_lookup_requires_api_key(self, mock_get, mcp_registry):
        """
        Given: No SMITHERY_API_KEY in environment
        When: Looking up Smithery server
        Then: Returns None (API key required)
        """
        # Ensure no API key is set
        with patch.dict('os.environ', {'SMITHERY_API_KEY': ''}, clear=False):
            mcp_registry.smithery_api_key = ""
            result = mcp_registry.get_smithery_server_info("some-server")

        assert result is None, (
            "Expected None when Smithery API key missing. "
            "Fix: Check for API key before making request"
        )
        mock_get.assert_not_called()

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_smithery_lookup_calls_correct_endpoint(
        self, mock_get, mcp_registry_with_smithery_key, mock_http_response
    ):
        """
        Given: Smithery API key configured
        When: Looking up server
        Then: Queries registry.smithery.ai/servers/{id}
        """
        mock_get.return_value = mock_http_response(200, {"deploymentUrl": "http://deploy.url"})

        mcp_registry_with_smithery_key.get_smithery_server_info("weather-server")

        call_url = mock_get.call_args[0][0]
        assert "registry.smithery.ai" in call_url, (
            f"Expected Smithery registry URL. Got: '{call_url}'. "
            f"Cause: Wrong registry URL used for Smithery. "
            f"Fix: Use 'https://registry.smithery.ai/servers/...' for Smithery lookups"
        )
        assert "weather-server" in call_url, (
            f"Expected server ID in URL. Got: '{call_url}'. "
            f"Cause: Server ID not included in URL path. "
            f"Fix: Append server_id to Smithery registry URL"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_smithery_lookup_includes_auth_header(
        self, mock_get, mcp_registry_with_smithery_key, mock_http_response
    ):
        """
        Given: Smithery API key configured
        When: Making request
        Then: Includes Authorization header
        """
        mock_get.return_value = mock_http_response(200, {"deploymentUrl": "http://test"})

        mcp_registry_with_smithery_key.get_smithery_server_info("server")

        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" in headers, (
            f"Expected Authorization header. Got headers: {headers}. "
            f"Cause: Auth header not added to request. "
            f"Fix: Add headers={{'Authorization': f'Bearer {{api_key}}'}} to request"
        )
        assert "Bearer" in headers["Authorization"], (
            f"Expected Bearer token. Got: '{headers.get('Authorization')}'. "
            f"Cause: Wrong auth format used. "
            f"Fix: Use 'Bearer {{api_key}}' format for Authorization header"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_smithery_returns_server_info_on_success(
        self, mock_get, mcp_registry_with_smithery_key, mock_http_response
    ):
        """
        Given: Smithery returns server info
        When: Looking up
        Then: Returns parsed server data
        """
        smithery_response = {
            "deploymentUrl": "http://deployed.smithery.ai/server",
            "description": "Weather API server",
            "connections": [{"type": "http", "deploymentUrl": "http://mcp.url"}]
        }
        mock_get.return_value = mock_http_response(200, smithery_response)

        result = mcp_registry_with_smithery_key.get_smithery_server_info("weather")

        assert result is not None, (
            "Expected server info dict. Got None. "
            "Cause: Success response not returned. "
            "Fix: Return response.json() on status 200"
        )
        assert result.get("deploymentUrl") == "http://deployed.smithery.ai/server", (
            f"Expected deploymentUrl in result. Got: {result}. "
            f"Cause: deploymentUrl field not preserved. "
            f"Fix: Include deploymentUrl in returned dict"
        )


# =============================================================================
# Tests: Server URL Construction
# =============================================================================

@skip_if_no_registry
class TestServerURLConstruction:
    """Tests for building MCP server URLs with authentication."""

    def test_nanda_url_uses_endpoint_directly(self, mcp_registry):
        """
        Given: NANDA registry server
        When: Building URL
        Then: Uses endpoint directly (no auth encoding)
        """
        result = mcp_registry.build_server_url(
            endpoint="http://nanda.server:8080/mcp",
            config={"param": "value"},
            registry_provider="nanda"
        )

        assert result == "http://nanda.server:8080/mcp", (
            f"Expected direct endpoint for NANDA. Got: '{result}'. "
            f"Cause: NANDA URL being modified. "
            f"Fix: Return endpoint directly for registry_provider='nanda'"
        )

    def test_smithery_url_includes_api_key(self, mcp_registry_with_smithery_key):
        """
        Given: Smithery registry server
        When: Building URL
        Then: Includes api_key parameter
        """
        result = mcp_registry_with_smithery_key.build_server_url(
            endpoint="http://smithery.server/mcp",
            config={"setting": "val"},
            registry_provider="smithery"
        )

        assert result is not None, (
            "Expected URL for Smithery. Got None. "
            "Cause: Smithery URL not built. "
            "Fix: Build URL with api_key for registry_provider='smithery'"
        )
        assert "api_key=" in result, (
            f"Expected api_key parameter in Smithery URL. Got: '{result}'. "
            f"Cause: API key not appended to URL. "
            f"Fix: Add ?api_key={{api_key}} to Smithery URLs"
        )

    def test_smithery_url_includes_base64_config(self, mcp_registry_with_smithery_key):
        """
        Given: Smithery server with config
        When: Building URL
        Then: Config is base64 encoded in URL
        """
        config = {"city": "Tokyo", "units": "metric"}
        result = mcp_registry_with_smithery_key.build_server_url(
            endpoint="http://smithery.server/mcp",
            config=config,
            registry_provider="smithery"
        )

        assert "config=" in result, (
            f"Expected config param in URL. Got: '{result}'. "
            f"Cause: Config not added as URL parameter. "
            f"Fix: Add config={{base64_encoded_config}} to URL"
        )
        # Verify config is properly encoded
        expected_b64 = base64.b64encode(json.dumps(config).encode()).decode()
        assert expected_b64 in result, (
            f"Expected base64 config '{expected_b64[:20]}...' in URL. "
            f"Got: '{result}'. "
            f"Cause: Config not properly base64 encoded. "
            f"Fix: Use base64.b64encode(json.dumps(config).encode()).decode()"
        )

    def test_smithery_url_returns_none_without_api_key(self, mcp_registry):
        """
        Given: No Smithery API key
        When: Building Smithery URL
        Then: Returns None
        """
        mcp_registry.smithery_api_key = ""

        result = mcp_registry.build_server_url(
            endpoint="http://smithery.server",
            config={},
            registry_provider="smithery"
        )

        assert result is None, (
            f"Expected None without API key. Got: '{result}'. "
            f"Cause: Smithery URL built without required API key. "
            f"Fix: Return None if smithery_api_key is empty for Smithery provider"
        )


# =============================================================================
# Tests: Unified Server Lookup
# =============================================================================

@skip_if_no_registry
class TestUnifiedServerLookup:
    """Tests for get_mcp_server_info() unified lookup method."""

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_routes_to_nanda_for_nanda_provider(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: registry_provider="nanda"
        When: Calling get_mcp_server_info()
        Then: Routes to NANDA lookup
        """
        mock_get.return_value = mock_http_response(200, {"server_url": "http://nanda.test"})

        result = mcp_registry.get_mcp_server_info("nanda", "my-server")

        call_url = mock_get.call_args[0][0]
        assert "mcp.registry.test" in call_url, (
            f"Expected NANDA registry URL. Got: '{call_url}'. "
            f"Cause: Wrong registry URL used. "
            f"Fix: Route to mcp_registry_url for registry_provider='nanda'"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_routes_to_smithery_for_smithery_provider(
        self, mock_get, mcp_registry_with_smithery_key, mock_http_response
    ):
        """
        Given: registry_provider="smithery"
        When: Calling get_mcp_server_info()
        Then: Routes to Smithery lookup
        """
        mock_get.return_value = mock_http_response(200, {"deploymentUrl": "http://smithery.test"})

        result = mcp_registry_with_smithery_key.get_mcp_server_info("smithery", "weather")

        call_url = mock_get.call_args[0][0]
        assert "smithery.ai" in call_url, (
            f"Expected Smithery registry URL. Got: '{call_url}'. "
            f"Cause: Wrong registry URL used. "
            f"Fix: Route to smithery.ai for registry_provider='smithery'"
        )

    def test_returns_none_for_unknown_provider(self, mcp_registry):
        """
        Given: Unknown registry provider
        When: Calling get_mcp_server_info()
        Then: Returns None
        """
        result = mcp_registry.get_mcp_server_info("unknown-provider", "server")

        assert result is None, (
            f"Expected None for unknown provider. Got: {result}. "
            f"Cause: Unknown provider not handled. "
            f"Fix: Return None when registry_provider not in ['nanda', 'smithery']"
        )


# =============================================================================
# Tests: MCP Client Result Parsing
# =============================================================================

@skip_if_no_client
class TestMCPClientResultParsing:
    """Tests for MCPClient JSON response parsing."""

    def test_parse_result_handles_plain_string(self, mcp_client):
        """
        Given: Plain string response
        When: Parsing
        Then: Returns string as-is
        """
        result = mcp_client._parse_result("Hello World")

        assert "Hello World" in result, (
            f"Expected plain string preserved. Got: '{result}'. "
            f"Cause: String content modified during parsing. "
            f"Fix: Return string as-is if not valid JSON"
        )

    def test_parse_result_formats_json_dict(self, mcp_client):
        """
        Given: JSON dict as string
        When: Parsing
        Then: Returns formatted key-value output
        """
        json_str = '{"temperature": 25, "city": "Tokyo"}'
        result = mcp_client._parse_result(json_str)

        assert "Temperature" in result or "temperature" in result.lower(), (
            f"Expected 'temperature' key in formatted output. Got: '{result}'. "
            f"Cause: JSON keys not included in output. "
            f"Fix: Format dict keys as human-readable text"
        )
        assert "25" in result, (
            f"Expected value '25' in output. Got: '{result}'. "
            f"Cause: JSON values not included in output. "
            f"Fix: Include dict values in formatted text"
        )

    def test_parse_result_handles_mcp_rpc_format(self, mcp_client):
        """
        Given: MCP JSON-RPC format response
        When: Parsing
        Then: Extracts text from artifacts
        """
        rpc_response = json.dumps({
            "result": {
                "artifacts": [{
                    "parts": [{"text": "Extracted content here"}]
                }]
            }
        })
        result = mcp_client._parse_result(rpc_response)

        assert "Extracted content" in result, (
            f"Expected extracted artifact text. Got: '{result}'. "
            f"Cause: MCP RPC artifacts not parsed. "
            f"Fix: Extract text from result.artifacts[].parts[].text"
        )

    def test_parse_result_handles_dict_directly(self, mcp_client):
        """
        Given: Dict object (not string)
        When: Parsing
        Then: Formats as readable output
        """
        data = {"status": "success", "count": 42}
        result = mcp_client._parse_result(data)

        assert "success" in result, (
            f"Expected 'success' in parsed output. Got: '{result}'. "
            f"Cause: Dict key not formatted into output. "
            f"Fix: Include all dict keys in formatted string"
        )
        assert "42" in result, (
            f"Expected '42' (count value) in parsed output. Got: '{result}'. "
            f"Cause: Dict value not formatted into output. "
            f"Fix: Include all dict values in formatted string"
        )

    def test_parse_result_handles_nested_dict(self, mcp_client):
        """
        Given: Nested dict structure
        When: Parsing
        Then: Formats nested keys properly
        """
        data = {
            "weather": {
                "temperature": 20,
                "humidity": 65
            }
        }
        result = mcp_client._parse_result(data)

        assert "weather" in result.lower(), (
            f"Expected 'weather' key in nested output. Got: '{result}'. "
            f"Cause: Nested dict keys not included. "
            f"Fix: Recursively format nested dict structures"
        )

    def test_parse_result_handles_list_data(self, mcp_client):
        """
        Given: List of items
        When: Parsing
        Then: Formats as numbered items
        """
        data = [
            {"name": "Item 1"},
            {"name": "Item 2"}
        ]
        result = mcp_client._parse_result(data)

        assert "Item 1" in result, (
            f"Expected 'Item 1' in list output. Got: '{result}'. "
            f"Cause: List items not formatted correctly. "
            f"Fix: Iterate and format each list item"
        )

    def test_parse_result_handles_invalid_json_gracefully(self, mcp_client):
        """
        Given: Invalid JSON string
        When: Parsing
        Then: Returns original string (not crash)
        """
        invalid = "Not JSON: {broken"
        result = mcp_client._parse_result(invalid)

        assert isinstance(result, str), (
            f"Expected string result on invalid JSON. Got: {type(result)}. "
            f"Cause: Invalid JSON not falling back to string. "
            f"Fix: Return original string if json.loads() fails"
        )
        # Should return something, not crash

    def test_format_json_response_limits_list_items(self, mcp_client):
        """
        Given: List with many items
        When: Formatting
        Then: Shows first items with "and X more" message

        Why: Prevents overwhelming output for large responses.
        """
        large_list = [{"id": i} for i in range(20)]
        result = mcp_client._format_json_response(large_list)

        assert "more" in result.lower(), (
            f"Expected 'more items' truncation message. Got: '{result}'. "
            f"Cause: Large list not truncated. "
            f"Fix: Show first N items and '...and X more items' message"
        )


# =============================================================================
# Tests: Agent Registry Config Lookup
# =============================================================================

@skip_if_no_registry
class TestAgentRegistryConfigLookup:
    """Tests for get_server_config() agent registry queries."""

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_queries_get_mcp_registry_endpoint(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Registry provider and qualified name
        When: Getting server config
        Then: Queries /get_mcp_registry with params
        """
        mock_get.return_value = mock_http_response(200, {
            "endpoint": "http://mcp.server",
            "config": "{}",
            "registry_provider": "nanda"
        })

        mcp_registry.get_server_config("nanda", "my-server")

        call_url = mock_get.call_args[0][0]
        assert "/get_mcp_registry" in call_url, (
            f"Expected /get_mcp_registry endpoint. Got: '{call_url}'. "
            f"Cause: Wrong endpoint URL used. "
            f"Fix: Use f'{{agent_registry_url}}/get_mcp_registry' for config lookup"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_passes_query_params(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Provider and qualified name
        When: Querying config
        Then: Includes both as query params
        """
        mock_get.return_value = mock_http_response(200, {
            "endpoint": "http://test",
            "config": "{}",
            "registry_provider": "nanda"
        })

        mcp_registry.get_server_config("smithery", "weather-api")

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params.get("registry_provider") == "smithery", (
            f"Expected registry_provider param. Got: {params}. "
            f"Cause: registry_provider not passed as query param. "
            f"Fix: Add params={{'registry_provider': provider}} to request"
        )
        assert params.get("qualified_name") == "weather-api", (
            f"Expected qualified_name param. Got: {params}. "
            f"Cause: qualified_name not passed as query param. "
            f"Fix: Add params={{'qualified_name': server_name}} to request"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_parses_config_json_string(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Config returned as JSON string
        When: Getting config
        Then: Parses to dict
        """
        mock_get.return_value = mock_http_response(200, {
            "endpoint": "http://test",
            "config": '{"api_version": "v2"}',
            "registry_provider": "nanda"
        })

        result = mcp_registry.get_server_config("nanda", "server")

        assert result["config"]["api_version"] == "v2", (
            f"Expected parsed config with api_version='v2'. Got: {result.get('config')}. "
            f"Cause: JSON string config not parsed. "
            f"Fix: Parse config if isinstance(config, str)"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_returns_none_on_error(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Registry returns error
        When: Getting config
        Then: Returns None
        """
        mock_get.return_value = mock_http_response(500)

        result = mcp_registry.get_server_config("nanda", "server")

        assert result is None, (
            f"Expected None on HTTP error (500). Got: {result}. "
            f"Cause: Error status not returning None. "
            f"Fix: Return None when status_code >= 400"
        )


# =============================================================================
# Tests: MCP Registry Edge Cases
# =============================================================================

@skip_if_no_registry
class TestMCPRegistryEdgeCases:
    """Tests for error handling and edge cases."""

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_handles_timeout_in_nanda_lookup(self, mock_get, mcp_registry):
        """
        Given: NANDA registry times out
        When: Looking up server
        Then: Returns None (not crash)
        """
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Request timeout")

        result = mcp_registry.get_nanda_mcp_server_info("server")

        assert result is None, (
            "Expected None on timeout. Got crash. "
            "Fix: Handle Timeout exception"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_handles_invalid_json_in_response(self, mock_get, mcp_registry, mock_http_response):
        """
        Given: Registry returns invalid JSON
        When: Parsing response
        Then: Returns None (not crash)
        """
        mock_resp = mock_http_response(200)
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_resp

        result = mcp_registry.get_nanda_mcp_server_info("server")

        # Should handle gracefully - return None or error dict, not crash
        assert result is None or isinstance(result, dict), (
            f"Expected None or error dict on invalid JSON. Got: {type(result)}. "
            f"Cause: ValueError from json parsing not caught. "
            f"Fix: Add try-except for json.JSONDecodeError returning None"
        )

    def test_build_url_handles_empty_config(self, mcp_registry_with_smithery_key):
        """
        Given: Empty config dict
        When: Building Smithery URL
        Then: Still includes base64 encoded empty object
        """
        result = mcp_registry_with_smithery_key.build_server_url(
            endpoint="http://test",
            config={},
            registry_provider="smithery"
        )

        assert result is not None, (
            "Expected URL even with empty config. Got None. "
            "Cause: Empty config dict not handled. "
            "Fix: Handle empty dict as valid config"
        )
        assert "config=" in result, (
            f"Expected config param in URL. Got: '{result}'. "
            f"Cause: Empty config not encoded. "
            f"Fix: Encode empty dict as base64('{{}}')"
        )

    @patch('nanda_core.core.mcp_registry.requests.get')
    def test_smithery_complete_info_chains_lookups(
        self, mock_get, mcp_registry_with_smithery_key, mock_http_response
    ):
        """
        Given: Smithery server exists
        When: Getting complete info
        Then: Combines server info and built URL
        """
        mock_get.return_value = mock_http_response(200, {
            "deploymentUrl": "http://deploy.smithery.ai/v1",
            "connections": [{"type": "http", "deploymentUrl": "http://mcp.endpoint"}],
            "description": "Test server"
        })

        result = mcp_registry_with_smithery_key.get_smithery_mcp_server_info_complete("test")

        assert result is not None, (
            "Expected complete info dict. Got None. "
            "Cause: Smithery complete lookup failed. "
            "Fix: Chain get_smithery_server_info and build_server_url"
        )
        assert_contains_all(result, ["server_name", "server_url", "registry_provider"], "complete info")
        assert result["registry_provider"] == "smithery", (
            f"Expected registry_provider='smithery'. Got: '{result.get('registry_provider')}'. "
            f"Cause: Provider not set in complete info. "
            f"Fix: Add registry_provider='smithery' to result dict"
        )

    def test_case_insensitive_registry_provider(self, mcp_registry):
        """
        Given: Registry provider in different case
        When: Getting server info
        Then: Matches case-insensitively
        """
        # Both "NANDA" and "nanda" should work
        with patch.object(mcp_registry, 'get_nanda_mcp_server_info') as mock_nanda:
            mock_nanda.return_value = {"server_url": "http://test"}

            result1 = mcp_registry.get_mcp_server_info("NANDA", "server")
            result2 = mcp_registry.get_mcp_server_info("nanda", "server")

            assert mock_nanda.call_count == 2, (
                "Expected both cases to route to NANDA lookup"
            )
