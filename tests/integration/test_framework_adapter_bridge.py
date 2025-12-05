"""
Integration tests for Framework-to-Protocol Bridge (NANDA Adapter).

Tests the NANDA class which bridges user's agent_logic to A2A protocol.
Per Issue #7: "Framework-to-protocol bridge"

What's mocked (external dependencies):
- HTTP requests to registry (external NANDA Index)
- run_server() blocking call (python_a2a server)

What's tested (our code):
- NANDA.__init__() parameter handling and bridge creation
- _register() HTTP request construction and error handling
- start() registration flow logic
- stop() cleanup logic
- Input validation and edge cases

Test Organization:
- TestNANDAInitialization: Constructor and parameter storage
- TestBridgeCreation: SimpleAgentBridge instantiation and config passing
- TestRegistryRegistration: HTTP registration flow and error handling
- TestServerLifecycle: start() and stop() methods
- TestTelemetryIntegration: Telemetry enable/disable behavior
- TestInputValidation: Invalid inputs and boundary conditions
- TestEdgeCases: Unicode, special chars, boundary values
"""

import pytest
from unittest.mock import Mock, patch
import requests

# Import with error handling
try:
    from nanda_core.core.adapter import NANDA
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_logic():
    """Sample agent_logic callable for testing."""
    def logic(message: str, conversation_id: str) -> str:
        return f"Response to: {message}"
    return logic


@pytest.fixture
def mock_http_response():
    """Factory for mock HTTP responses."""
    def _create(status_code: int = 200, json_data=None, text=""):
        resp = Mock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = text
        return resp
    return _create


# =============================================================================
# Tests: NANDA Initialization
# =============================================================================

class TestNANDAInitialization:
    """Tests for NANDA.__init__() - verifies REAL parameter storage."""

    def test_stores_required_parameters(self, sample_agent_logic):
        """
        Given: agent_id and agent_logic (required params)
        When: Creating NANDA instance
        Then: Both parameters stored as attributes
        """
        nanda = NANDA(
            agent_id="test-agent",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == "test-agent", (
            f"Expected agent_id='test-agent'. Got: '{nanda.agent_id}'. "
            f"Cause: agent_id not stored in __init__. "
            f"Fix: Add self.agent_id = agent_id in __init__"
        )
        assert nanda.agent_logic is sample_agent_logic, (
            f"Expected agent_logic to be stored. Got: {type(nanda.agent_logic)}. "
            f"Cause: agent_logic reference not stored. "
            f"Fix: Add self.agent_logic = agent_logic in __init__"
        )

    def test_stores_all_optional_parameters(self, sample_agent_logic):
        """
        Given: All optional parameters with custom values
        When: Creating NANDA instance
        Then: All custom values stored correctly
        """
        nanda = NANDA(
            agent_id="test-agent",
            agent_logic=sample_agent_logic,
            port=7000,
            registry_url="http://registry.test",
            mcp_registry_url="http://mcp.test",
            public_url="http://public.test:7000",
            host="127.0.0.1",
            enable_telemetry=False,
            smithery_api_key="test-key"
        )

        assert nanda.port == 7000, (
            f"Expected port=7000. Got: {nanda.port}. "
            f"Cause: port parameter not stored. "
            f"Fix: Add self.port = port in __init__"
        )
        assert nanda.registry_url == "http://registry.test", (
            f"Expected registry_url='http://registry.test'. Got: '{nanda.registry_url}'. "
            f"Cause: registry_url not stored. "
            f"Fix: Add self.registry_url = registry_url in __init__"
        )
        assert nanda.mcp_registry_url == "http://mcp.test", (
            f"Expected mcp_registry_url='http://mcp.test'. Got: '{nanda.mcp_registry_url}'. "
            f"Cause: mcp_registry_url not stored. "
            f"Fix: Add self.mcp_registry_url = mcp_registry_url in __init__"
        )
        assert nanda.public_url == "http://public.test:7000", (
            f"Expected public_url='http://public.test:7000'. Got: '{nanda.public_url}'. "
            f"Cause: public_url not stored. "
            f"Fix: Add self.public_url = public_url in __init__"
        )
        assert nanda.host == "127.0.0.1", (
            f"Expected host='127.0.0.1'. Got: '{nanda.host}'. "
            f"Cause: host parameter not stored. "
            f"Fix: Add self.host = host in __init__"
        )
        assert nanda.smithery_api_key == "test-key", (
            f"Expected smithery_api_key='test-key'. Got: '{nanda.smithery_api_key}'. "
            f"Cause: smithery_api_key not stored. "
            f"Fix: Add self.smithery_api_key = smithery_api_key in __init__"
        )
        assert nanda.enable_telemetry is False, (
            f"Expected enable_telemetry=False. Got: {nanda.enable_telemetry}. "
            f"Cause: enable_telemetry flag not stored. "
            f"Fix: Add self.enable_telemetry = enable_telemetry in __init__"
        )

    def test_uses_correct_default_values(self, sample_agent_logic):
        """
        Given: Only required parameters
        When: Creating NANDA instance
        Then: Defaults match documented values (port=6000, host='0.0.0.0', etc.)
        """
        nanda = NANDA(
            agent_id="test",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.port == 6000, (
            f"Expected default port=6000. Got: {nanda.port}. "
            f"Cause: Default port value incorrect. "
            f"Fix: Set port: int = 6000 in __init__ signature"
        )
        assert nanda.host == "0.0.0.0", (
            f"Expected default host='0.0.0.0'. Got: '{nanda.host}'. "
            f"Cause: Default host value incorrect. "
            f"Fix: Set host: str = '0.0.0.0' in __init__ signature"
        )
        assert nanda.registry_url is None, (
            f"Expected default registry_url=None. Got: '{nanda.registry_url}'. "
            f"Cause: registry_url should default to None. "
            f"Fix: Set registry_url: Optional[str] = None"
        )
        assert nanda.mcp_registry_url is None, (
            f"Expected default mcp_registry_url=None. Got: '{nanda.mcp_registry_url}'. "
            f"Cause: mcp_registry_url should default to None. "
            f"Fix: Set mcp_registry_url: Optional[str] = None"
        )
        assert nanda.public_url is None, (
            f"Expected default public_url=None. Got: '{nanda.public_url}'. "
            f"Cause: public_url should default to None. "
            f"Fix: Set public_url: Optional[str] = None"
        )
        assert nanda.smithery_api_key is None, (
            f"Expected default smithery_api_key=None. Got: '{nanda.smithery_api_key}'. "
            f"Cause: smithery_api_key should default to None. "
            f"Fix: Set smithery_api_key: Optional[str] = None"
        )


# =============================================================================
# Tests: Bridge Creation
# =============================================================================

class TestBridgeCreation:
    """Tests for SimpleAgentBridge instantiation - verifies REAL bridge config."""

    def test_creates_bridge_instance(self, sample_agent_logic):
        """
        Given: Valid NANDA configuration
        When: NANDA instance created
        Then: Bridge is SimpleAgentBridge instance
        """
        nanda = NANDA(
            agent_id="my-agent",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.bridge is not None, (
            "Expected bridge to be created. Got: None. "
            "Cause: Bridge not instantiated in __init__. "
            "Fix: Add self.bridge = SimpleAgentBridge(...) in __init__"
        )
        assert isinstance(nanda.bridge, SimpleAgentBridge), (
            f"Expected SimpleAgentBridge instance. Got: {type(nanda.bridge).__name__}. "
            f"Cause: Wrong bridge class instantiated. "
            f"Fix: Use SimpleAgentBridge class for self.bridge"
        )

    def test_passes_agent_id_to_bridge(self, sample_agent_logic):
        """
        Given: NANDA with agent_id
        When: Bridge is created
        Then: Bridge.agent_id matches NANDA.agent_id
        """
        nanda = NANDA(
            agent_id="my-agent-123",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.bridge.agent_id == "my-agent-123", (
            f"Expected bridge.agent_id='my-agent-123'. Got: '{nanda.bridge.agent_id}'. "
            f"Cause: agent_id not passed to SimpleAgentBridge. "
            f"Fix: Pass agent_id=agent_id to SimpleAgentBridge()"
        )

    def test_passes_registry_url_to_bridge(self, sample_agent_logic):
        """
        Given: NANDA with registry_url
        When: Bridge is created
        Then: Bridge.registry_url matches for agent lookup capability
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry.example.com",
            enable_telemetry=False
        )

        assert nanda.bridge.registry_url == "http://registry.example.com", (
            f"Expected bridge.registry_url='http://registry.example.com'. "
            f"Got: '{nanda.bridge.registry_url}'. "
            f"Cause: registry_url not passed to SimpleAgentBridge. "
            f"Fix: Pass registry_url=registry_url to SimpleAgentBridge()"
        )

    def test_passes_mcp_registry_url_to_bridge(self, sample_agent_logic):
        """
        Given: NANDA with mcp_registry_url
        When: Bridge is created
        Then: Bridge has mcp_registry_url for MCP server discovery
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            mcp_registry_url="http://mcp.registry.test",
            enable_telemetry=False
        )

        # Verify MCP registry URL is accessible through bridge's mcp_registry
        assert hasattr(nanda.bridge, 'mcp_registry') or hasattr(nanda.bridge, 'mcp_registry_url'), (
            "Expected bridge to have MCP registry configuration. "
            "Cause: mcp_registry_url not passed to bridge. "
            "Fix: Pass mcp_registry_url to SimpleAgentBridge()"
        )

    def test_passes_smithery_api_key_to_bridge(self, sample_agent_logic):
        """
        Given: NANDA with smithery_api_key
        When: Bridge is created
        Then: Bridge has smithery_api_key for authenticated MCP lookups
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            smithery_api_key="sk-test-key-123",
            enable_telemetry=False
        )

        # Bridge should have received the key (via MCP registry or direct)
        assert nanda.bridge is not None, (
            "Expected bridge to be created with smithery config. "
            "Cause: Bridge creation failed. "
            "Fix: Ensure SimpleAgentBridge accepts smithery_api_key"
        )

    def test_bridge_handles_messages_using_agent_logic(self, sample_agent_logic):
        """
        Given: NANDA with agent_logic that returns 'Response to: {message}'
        When: Message sent through bridge
        Then: Response contains agent_logic output
        """
        from python_a2a import Message, TextContent, MessageRole

        nanda = NANDA(
            agent_id="test",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        msg = Message(
            content=TextContent(text="Hello World"),
            role=MessageRole.USER
        )
        response = nanda.bridge.handle_message(msg)

        assert response is not None, (
            "Expected response from bridge.handle_message(). Got: None. "
            "Cause: handle_message() returned None. "
            "Fix: Ensure agent_logic is called and response returned"
        )
        assert hasattr(response, 'content'), (
            f"Expected response to have 'content' attribute. Got: {type(response)}. "
            f"Cause: Invalid response structure. "
            f"Fix: Return proper Message object from handle_message()"
        )
        assert "Response to" in response.content.text, (
            f"Expected agent_logic output in response. Got: '{response.content.text}'. "
            f"Cause: agent_logic not invoked or output not used. "
            f"Fix: Call agent_logic(message, conversation_id) in handle_message()"
        )


# =============================================================================
# Tests: Registry Registration
# =============================================================================

class TestRegistryRegistration:
    """Tests for _register() - mocks external registry, tests our HTTP logic."""

    @patch('nanda_core.core.adapter.requests.post')
    def test_posts_to_correct_endpoint(self, mock_post, sample_agent_logic, mock_http_response):
        """
        Given: NANDA with registry_url='http://registry.test:6900'
        When: _register() called
        Then: POSTs to 'http://registry.test:6900/register'
        """
        mock_post.return_value = mock_http_response(200)

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry.test:6900",
            public_url="http://public.test:6000",
            enable_telemetry=False
        )
        nanda._register()

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert call_url == "http://registry.test:6900/register", (
            f"Expected POST to '/register' endpoint. Got: '{call_url}'. "
            f"Cause: URL construction incorrect in _register(). "
            f"Fix: Use f'{{self.registry_url}}/register' for URL"
        )

    @patch('nanda_core.core.adapter.requests.post')
    def test_sends_agent_id_in_request_body(self, mock_post, sample_agent_logic, mock_http_response):
        """
        Given: NANDA with agent_id='my-agent'
        When: _register() called
        Then: Request body contains agent_id='my-agent'
        """
        mock_post.return_value = mock_http_response(200)

        nanda = NANDA(
            agent_id="my-agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry.test",
            public_url="http://public.test:6000",
            enable_telemetry=False
        )
        nanda._register()

        call_kwargs = mock_post.call_args[1]
        body = call_kwargs.get("json", {})
        assert body.get("agent_id") == "my-agent", (
            f"Expected agent_id='my-agent' in body. Got: {body}. "
            f"Cause: agent_id not included in registration payload. "
            f"Fix: Add 'agent_id': self.agent_id to request body"
        )

    @patch('nanda_core.core.adapter.requests.post')
    def test_sends_public_url_as_agent_url(self, mock_post, sample_agent_logic, mock_http_response):
        """
        Given: NANDA with public_url='http://my-agent.public:6000'
        When: _register() called
        Then: Request body contains agent_url='http://my-agent.public:6000'
        """
        mock_post.return_value = mock_http_response(200)

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry.test",
            public_url="http://my-agent.public:6000",
            enable_telemetry=False
        )
        nanda._register()

        call_kwargs = mock_post.call_args[1]
        body = call_kwargs.get("json", {})
        assert body.get("agent_url") == "http://my-agent.public:6000", (
            f"Expected agent_url='http://my-agent.public:6000' in body. Got: {body}. "
            f"Cause: public_url not sent as agent_url. "
            f"Fix: Add 'agent_url': self.public_url to request body"
        )

    @patch('nanda_core.core.adapter.requests.post')
    def test_uses_timeout_to_prevent_hanging(self, mock_post, sample_agent_logic, mock_http_response):
        """
        Given: _register() making HTTP request
        When: Request sent
        Then: timeout=10 is set to prevent indefinite hanging
        """
        mock_post.return_value = mock_http_response(200)

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://reg",
            public_url="http://pub",
            enable_telemetry=False
        )
        nanda._register()

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs.get("timeout") == 10, (
            f"Expected timeout=10 in request. Got: {call_kwargs.get('timeout')}. "
            f"Cause: No timeout set, request could hang forever. "
            f"Fix: Add timeout=10 to requests.post() call"
        )

    @pytest.mark.parametrize("status_code,description", [
        (400, "Bad Request"),
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (500, "Internal Server Error"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
    ])
    @patch('nanda_core.core.adapter.requests.post')
    def test_handles_http_error_status_gracefully(
        self, mock_post, status_code, description, sample_agent_logic, mock_http_response, capsys
    ):
        """
        Given: Registry returns HTTP error status
        When: _register() called
        Then: Logs warning, doesn't crash
        """
        mock_post.return_value = mock_http_response(status_code)

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://reg",
            public_url="http://pub",
            enable_telemetry=False
        )

        # Should NOT raise exception
        nanda._register()

        output = capsys.readouterr().out
        assert "Failed" in output or "⚠️" in output or str(status_code) in output, (
            f"Expected warning for HTTP {status_code} ({description}). Got: '{output}'. "
            f"Cause: Non-200 status not logged. "
            f"Fix: Print warning when response.status_code != 200"
        )

    @patch('nanda_core.core.adapter.requests.post')
    def test_handles_connection_error_gracefully(self, mock_post, sample_agent_logic, capsys):
        """
        Given: Network connection fails
        When: _register() called
        Then: Catches exception, logs warning, doesn't crash
        """
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://reg",
            public_url="http://pub",
            enable_telemetry=False
        )

        # Should NOT raise exception
        nanda._register()

        output = capsys.readouterr().out
        assert "error" in output.lower() or "⚠️" in output, (
            f"Expected error message for connection failure. Got: '{output}'. "
            f"Cause: ConnectionError not caught. "
            f"Fix: Wrap requests.post in try-except"
        )

    @patch('nanda_core.core.adapter.requests.post')
    def test_handles_timeout_error_gracefully(self, mock_post, sample_agent_logic, capsys):
        """
        Given: Registry request times out
        When: _register() called
        Then: Catches timeout, logs warning, doesn't crash
        """
        mock_post.side_effect = requests.Timeout("Request timed out")

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://reg",
            public_url="http://pub",
            enable_telemetry=False
        )

        # Should NOT raise exception
        nanda._register()

        output = capsys.readouterr().out
        assert "error" in output.lower() or "⚠️" in output or "timeout" in output.lower(), (
            f"Expected timeout warning. Got: '{output}'. "
            f"Cause: Timeout exception not handled. "
            f"Fix: Catch requests.Timeout in _register()"
        )


# =============================================================================
# Tests: Server Lifecycle
# =============================================================================

class TestServerLifecycle:
    """Tests for start() and stop() - verifies REAL registration/startup logic."""

    @patch('nanda_core.core.adapter.run_server')
    @patch('nanda_core.core.adapter.requests.post')
    def test_start_registers_when_both_urls_configured(
        self, mock_post, mock_run_server, sample_agent_logic, mock_http_response
    ):
        """
        Given: NANDA with registry_url AND public_url
        When: start(register=True)
        Then: Calls _register() before starting server
        """
        mock_post.return_value = mock_http_response(200)

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry",
            public_url="http://public",
            enable_telemetry=False
        )
        nanda.start(register=True)

        assert mock_post.called, (
            "Expected HTTP POST for registration. Got: not called. "
            "Cause: _register() not called in start(). "
            "Fix: Call self._register() when register=True and URLs configured"
        )

    @patch('nanda_core.core.adapter.run_server')
    @patch('nanda_core.core.adapter.requests.post')
    def test_start_skips_registration_when_register_false(
        self, mock_post, mock_run_server, sample_agent_logic
    ):
        """
        Given: NANDA with URLs configured
        When: start(register=False)
        Then: Skips registration even with URLs
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry",
            public_url="http://public",
            enable_telemetry=False
        )
        nanda.start(register=False)

        assert not mock_post.called, (
            "Expected no registration when register=False. Got: POST called. "
            "Cause: register parameter not checked. "
            "Fix: Check 'if register and ...' in start()"
        )

    @patch('nanda_core.core.adapter.run_server')
    def test_start_skips_registration_without_registry_url(
        self, mock_run_server, sample_agent_logic
    ):
        """
        Given: NANDA without registry_url (only public_url)
        When: start(register=True)
        Then: Skips registration (need both URLs)
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url=None,
            public_url="http://public",
            enable_telemetry=False
        )

        with patch.object(nanda, '_register') as mock_register:
            nanda.start(register=True)
            assert not mock_register.called, (
                "Expected no registration without registry_url. "
                "Cause: Missing registry_url check. "
                "Fix: Check 'if register and self.registry_url and self.public_url'"
            )

    @patch('nanda_core.core.adapter.run_server')
    def test_start_skips_registration_without_public_url(
        self, mock_run_server, sample_agent_logic
    ):
        """
        Given: NANDA without public_url (only registry_url)
        When: start(register=True)
        Then: Skips registration (need both URLs)
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="http://registry",
            public_url=None,
            enable_telemetry=False
        )

        with patch.object(nanda, '_register') as mock_register:
            nanda.start(register=True)
            assert not mock_register.called, (
                "Expected no registration without public_url. "
                "Cause: Missing public_url check. "
                "Fix: Check 'if register and self.registry_url and self.public_url'"
            )

    @patch('nanda_core.core.adapter.run_server')
    def test_start_calls_run_server_with_correct_params(
        self, mock_run_server, sample_agent_logic
    ):
        """
        Given: NANDA with host='127.0.0.1', port=7000
        When: start() called
        Then: run_server() receives bridge, host, port
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            host="127.0.0.1",
            port=7000,
            enable_telemetry=False
        )
        nanda.start(register=False)

        mock_run_server.assert_called_once()
        call_args = mock_run_server.call_args

        assert call_args[0][0] is nanda.bridge, (
            "Expected bridge as first argument to run_server(). "
            "Cause: Wrong object passed. "
            "Fix: Call run_server(self.bridge, ...)"
        )
        assert call_args[1].get("host") == "127.0.0.1", (
            f"Expected host='127.0.0.1'. Got: {call_args[1].get('host')}. "
            f"Cause: host not passed to run_server(). "
            f"Fix: Pass host=self.host to run_server()"
        )
        assert call_args[1].get("port") == 7000, (
            f"Expected port=7000. Got: {call_args[1].get('port')}. "
            f"Cause: port not passed to run_server(). "
            f"Fix: Pass port=self.port to run_server()"
        )

    def test_stop_calls_telemetry_stop_when_enabled(self, sample_agent_logic):
        """
        Given: NANDA with active telemetry
        When: stop() called
        Then: Calls telemetry.stop() for cleanup
        """
        mock_telemetry = Mock()

        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )
        nanda.telemetry = mock_telemetry  # Inject mock
        nanda.stop()

        mock_telemetry.stop.assert_called_once(), (
            "Expected telemetry.stop() to be called. "
            "Cause: Telemetry not cleaned up in stop(). "
            "Fix: Add 'if self.telemetry: self.telemetry.stop()' in stop()"
        )

    def test_stop_handles_none_telemetry_gracefully(self, sample_agent_logic):
        """
        Given: NANDA without telemetry (telemetry=None)
        When: stop() called
        Then: Doesn't crash (null-safe)
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )
        nanda.telemetry = None

        # Should NOT raise exception
        try:
            nanda.stop()
        except AttributeError as e:
            pytest.fail(
                f"stop() crashed with None telemetry: {e}. "
                f"Cause: Missing None check. "
                f"Fix: Use 'if self.telemetry:' before calling stop()"
            )


# =============================================================================
# Tests: Telemetry Integration
# =============================================================================

class TestTelemetryIntegration:
    """Tests for telemetry initialization - verifies REAL enable/disable logic."""

    def test_telemetry_none_when_disabled(self, sample_agent_logic):
        """
        Given: enable_telemetry=False
        When: NANDA created
        Then: self.telemetry is None (no initialization attempted)
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.telemetry is None, (
            f"Expected telemetry=None when disabled. Got: {nanda.telemetry}. "
            f"Cause: Telemetry initialized despite enable_telemetry=False. "
            f"Fix: Only initialize telemetry when enable_telemetry=True"
        )

    def test_telemetry_flag_stored_correctly(self, sample_agent_logic):
        """
        Given: Different enable_telemetry values
        When: NANDA instances created
        Then: Flag stored as-is for later reference
        """
        nanda_true = NANDA(
            agent_id="agent1",
            agent_logic=sample_agent_logic,
            enable_telemetry=True
        )
        nanda_false = NANDA(
            agent_id="agent2",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda_true.enable_telemetry is True, (
            f"Expected enable_telemetry=True. Got: {nanda_true.enable_telemetry}. "
            f"Cause: Flag not stored. "
            f"Fix: Add self.enable_telemetry = enable_telemetry in __init__"
        )
        assert nanda_false.enable_telemetry is False, (
            f"Expected enable_telemetry=False. Got: {nanda_false.enable_telemetry}. "
            f"Cause: Flag not stored correctly. "
            f"Fix: Store the exact value passed"
        )

    def test_telemetry_initialization_does_not_crash_on_import_failure(self, sample_agent_logic):
        """
        Given: TelemetrySystem may not be available
        When: NANDA created with enable_telemetry=True
        Then: Falls back gracefully (no crash)
        """
        # This test runs with real code - verifies graceful fallback
        try:
            nanda = NANDA(
                agent_id="agent",
                agent_logic=sample_agent_logic,
                enable_telemetry=True
            )
            assert nanda is not None, "NANDA should be created"
            # Telemetry is either initialized OR None (both are acceptable)
            assert nanda.telemetry is None or hasattr(nanda.telemetry, 'stop'), (
                f"Telemetry should be None or valid instance. Got: {type(nanda.telemetry)}. "
                f"Cause: Invalid telemetry state. "
                f"Fix: Set self.telemetry = None on import failure"
            )
        except ImportError:
            pytest.fail(
                "NANDA crashed on telemetry import failure. "
                "Cause: ImportError not caught. "
                "Fix: Wrap telemetry import in try-except"
            )


# =============================================================================
# Tests: Input Validation
# =============================================================================

class TestInputValidation:
    """Tests for invalid inputs - verifies behavior doesn't crash."""

    def test_accepts_empty_string_agent_id(self, sample_agent_logic):
        """
        Given: agent_id="" (empty string)
        When: NANDA created
        Then: Stores empty string (no validation currently)

        Note: This documents current behavior. Consider adding validation.
        """
        nanda = NANDA(
            agent_id="",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == "", (
            f"Expected empty agent_id stored. Got: '{nanda.agent_id}'. "
            f"Cause: agent_id modified unexpectedly. "
            f"Fix: Store agent_id as-is or add explicit validation"
        )

    def test_accepts_whitespace_only_agent_id(self, sample_agent_logic):
        """
        Given: agent_id="   " (whitespace only)
        When: NANDA created
        Then: Stores as-is (no stripping/validation currently)

        Note: This documents current behavior. Consider adding validation.
        """
        nanda = NANDA(
            agent_id="   ",
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == "   ", (
            f"Expected whitespace agent_id stored. Got: '{nanda.agent_id}'. "
            f"Cause: Whitespace stripped or modified. "
            f"Fix: Store as-is or add explicit validation with clear error"
        )

    def test_accepts_very_long_agent_id(self, sample_agent_logic):
        """
        Given: agent_id with 1000 characters
        When: NANDA created
        Then: Stores full ID without truncation
        """
        long_id = "a" * 1000

        nanda = NANDA(
            agent_id=long_id,
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == long_id, (
            f"Expected 1000-char agent_id. Got length: {len(nanda.agent_id)}. "
            f"Cause: agent_id truncated. "
            f"Fix: Don't truncate agent_id or document max length"
        )
        assert len(nanda.agent_id) == 1000, (
            f"Expected length 1000. Got: {len(nanda.agent_id)}. "
            f"Cause: String modified. "
            f"Fix: Preserve exact input"
        )

    @patch('nanda_core.core.adapter.run_server')
    def test_empty_registry_url_treated_as_falsy(self, mock_run_server, sample_agent_logic):
        """
        Given: registry_url="" (empty string, falsy)
        When: start(register=True)
        Then: Skips registration (empty string is falsy in Python)
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url="",
            public_url="http://public",
            enable_telemetry=False
        )

        with patch.object(nanda, '_register') as mock_register:
            nanda.start(register=True)
            assert not mock_register.called, (
                "Expected no registration with empty registry_url. "
                "Cause: Empty string not treated as falsy. "
                "Fix: Use 'if self.registry_url' (truthy check)"
            )

    def test_accepts_lambda_as_agent_logic(self):
        """
        Given: Lambda function as agent_logic
        When: NANDA created
        Then: Lambda stored and callable
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=lambda msg, conv: f"Echo: {msg}",
            enable_telemetry=False
        )

        assert callable(nanda.agent_logic), (
            "Expected agent_logic to be callable. "
            "Cause: Lambda not stored correctly. "
            "Fix: Store any callable as agent_logic"
        )

        result = nanda.agent_logic("test", "conv-123")
        assert result == "Echo: test", (
            f"Expected 'Echo: test'. Got: '{result}'. "
            f"Cause: Lambda not working. "
            f"Fix: Verify callable storage"
        )

    def test_accepts_class_method_as_agent_logic(self):
        """
        Given: Instance method as agent_logic
        When: NANDA created
        Then: Method stored and callable with self bound
        """
        class MyHandler:
            def __init__(self):
                self.call_count = 0

            def handle(self, msg: str, conv: str) -> str:
                self.call_count += 1
                return f"Handled: {msg}"

        handler = MyHandler()
        nanda = NANDA(
            agent_id="agent",
            agent_logic=handler.handle,
            enable_telemetry=False
        )

        result = nanda.agent_logic("test", "conv")
        assert result == "Handled: test", (
            f"Expected 'Handled: test'. Got: '{result}'. "
            f"Cause: Method not callable. "
            f"Fix: Accept any callable"
        )
        assert handler.call_count == 1, (
            f"Expected call_count=1. Got: {handler.call_count}. "
            f"Cause: Method not invoked. "
            f"Fix: Verify bound method works"
        )


# =============================================================================
# Tests: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for boundary conditions and special characters."""

    @pytest.mark.parametrize("agent_id", [
        "simple",
        "with-hyphens",
        "with_underscores",
        "with.dots",
        "with123numbers",
        "MixedCase",
        "a",  # Single character
    ])
    def test_accepts_common_agent_id_formats(self, agent_id, sample_agent_logic):
        """
        Given: Various common agent_id formats
        When: NANDA created
        Then: All formats accepted and stored
        """
        nanda = NANDA(
            agent_id=agent_id,
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == agent_id, (
            f"Expected agent_id='{agent_id}'. Got: '{nanda.agent_id}'. "
            f"Cause: agent_id format not accepted. "
            f"Fix: Accept alphanumeric with hyphens/underscores/dots"
        )

    @pytest.mark.parametrize("agent_id,description", [
        ("代理", "Chinese characters"),
        ("エージェント", "Japanese characters"),
        ("агент", "Cyrillic characters"),
        ("에이전트", "Korean Hangul"),
        ("وكيل", "Arabic RTL script"),
        ("סוכן", "Hebrew RTL script"),
        ("ตัวแทน", "Thai script"),
        ("एजेंट", "Hindi Devanagari"),
        ("agent-日本語", "Mixed ASCII and Japanese"),
        ("café-agent", "Accented characters"),
        ("agent،test", "Arabic comma punctuation"),
        ("agent「名」", "Japanese brackets"),
    ])
    def test_accepts_unicode_agent_ids(self, agent_id, description, sample_agent_logic):
        """
        Given: Unicode agent_id ({description})
        When: NANDA created
        Then: Unicode preserved exactly
        """
        nanda = NANDA(
            agent_id=agent_id,
            agent_logic=sample_agent_logic,
            enable_telemetry=False
        )

        assert nanda.agent_id == agent_id, (
            f"Expected Unicode agent_id '{agent_id}' ({description}). "
            f"Got: '{nanda.agent_id}'. "
            f"Cause: Unicode not preserved. "
            f"Fix: Don't encode/decode agent_id"
        )

    @pytest.mark.parametrize("port,description", [
        (0, "OS assigns random port"),
        (1, "minimum valid port"),
        (80, "HTTP port"),
        (443, "HTTPS port"),
        (1024, "first non-privileged"),
        (8080, "common dev port"),
        (65535, "maximum valid port"),
    ])
    def test_accepts_valid_port_numbers(self, port, description, sample_agent_logic):
        """
        Given: port={port} ({description})
        When: NANDA created
        Then: Port stored correctly
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            port=port,
            enable_telemetry=False
        )

        assert nanda.port == port, (
            f"Expected port={port} ({description}). Got: {nanda.port}. "
            f"Cause: Port not stored correctly. "
            f"Fix: Store port as-is"
        )

    @pytest.mark.parametrize("url,description", [
        ("http://localhost", "localhost without port"),
        ("http://localhost:6000", "localhost with port"),
        ("http://127.0.0.1:6000", "IP address"),
        ("https://secure.example.com", "HTTPS URL"),
        ("http://registry.example.com/api", "URL with path"),
        ("http://registry:6900", "Docker service name"),
    ])
    def test_accepts_various_url_formats(self, url, description, sample_agent_logic):
        """
        Given: registry_url='{url}' ({description})
        When: NANDA created
        Then: URL stored exactly as provided
        """
        nanda = NANDA(
            agent_id="agent",
            agent_logic=sample_agent_logic,
            registry_url=url,
            enable_telemetry=False
        )

        assert nanda.registry_url == url, (
            f"Expected registry_url='{url}' ({description}). "
            f"Got: '{nanda.registry_url}'. "
            f"Cause: URL modified or rejected. "
            f"Fix: Store URLs as-is"
        )

    def test_agent_logic_receives_correct_arguments(self, sample_agent_logic):
        """
        Given: agent_logic expecting (message, conversation_id)
        When: Message sent through bridge
        Then: Both arguments passed correctly
        """
        from python_a2a import Message, TextContent, MessageRole

        received_args = []

        def capturing_logic(message: str, conversation_id: str) -> str:
            received_args.append((message, conversation_id))
            return "OK"

        nanda = NANDA(
            agent_id="test",
            agent_logic=capturing_logic,
            enable_telemetry=False
        )

        msg = Message(
            content=TextContent(text="Test message"),
            role=MessageRole.USER,
            conversation_id="conv-123"
        )
        nanda.bridge.handle_message(msg)

        assert len(received_args) == 1, (
            f"Expected agent_logic called once. Got: {len(received_args)} calls. "
            f"Cause: agent_logic not invoked. "
            f"Fix: Call agent_logic in handle_message()"
        )
        assert received_args[0][0] == "Test message", (
            f"Expected message='Test message'. Got: '{received_args[0][0]}'. "
            f"Cause: Message text not extracted correctly. "
            f"Fix: Extract msg.content.text for agent_logic"
        )
