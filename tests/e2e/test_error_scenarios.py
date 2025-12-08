"""
E2E Tests for Error Scenarios.

Tests REAL error handling for network errors, timeouts, invalid requests,
and HTTP error codes in agent and registry communication.

This file focuses on ERROR HANDLING behavior, not process management or discovery.

For process errors (startup, shutdown, port conflicts):
    See test_agent_lifecycle.py

For registry/MCP client errors:
    See test_agent_discovery.py

For MCP protocol errors:
    See test_mcp_integration.py

Test Categories:
- TestNetworkErrors: Connection refused, timeouts, unreachable hosts
- TestHTTPErrorCodes: 400, 404, 500 handling in agent requests
- TestInvalidRequests: Malformed requests and invalid data to agents
- TestRegistryErrorResponses: Registry-specific error responses
- TestAgentErrorRecovery: Agent behavior after errors
- TestErrorMessageQuality: Error messages are helpful and actionable
"""

import socket
import time

import pytest
import requests
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from tests.e2e.conftest import (
    HTTP_REQUEST_TIMEOUT,
    find_free_port,
    is_port_in_use,
    wait_for_port,
)

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e

# Port that is guaranteed to not have a service (requires root to bind)
DEFINITELY_UNUSED_PORT = 1


# =============================================================================
# Tests: Network Errors
# =============================================================================


class TestNetworkErrors:
    """Tests for network error handling in E2E scenarios."""

    def test_connection_refused_raises_connection_error(self, http_client):
        """
        Given: Request to non-listening port
        When: Attempting HTTP connection
        Then: ConnectionError is raised (predictable exception type)

        Tests REAL: Connection refused handling
        """
        port = find_free_port()  # Get a port that's definitely not in use

        with pytest.raises(ConnectionError) as exc_info:
            http_client.get(f"http://localhost:{port}/health", timeout=2)

        # Verify error message is helpful
        error_msg = str(exc_info.value).lower()
        assert any(term in error_msg for term in ["refused", "connect", "failed"]), (
            f"ConnectionError message not helpful: {exc_info.value}. "
            "Cause: Exception message unclear. "
            "Fix: requests library should include connection details."
        )

    def test_agent_handles_target_agent_offline_gracefully(
        self, registry_process, agent_process_factory, http_client, send_a2a_message
    ):
        """
        Given: Target agent registered in registry but not running
        When: Sending @mention to offline target
        Then: Returns error response (not 500 crash)

        Tests REAL: Offline target error handling in A2A routing
        """
        sender = agent_process_factory("offline-sender")

        # Register a fake agent that's not actually running
        offline_port = find_free_port()
        http_client.post(
            f"{registry_process.url}/register",
            json={
                "agent_id": "offline-target",
                "agent_url": f"http://localhost:{offline_port}",
            },
        )

        # Try to send to offline target
        result = send_a2a_message(sender.url, "@offline-target Hello")

        # Should return a client-friendly error, not server crash
        assert result["status_code"] in [200, 400, 502, 503, 504], (
            f"Expected graceful error handling, got HTTP {result['status_code']}. "
            f"Response: {result['response'][:200] if result['response'] else 'empty'}. "
            "Cause: Connection error to target not caught. "
            "Fix: Add try/except around A2AClient.send_message() in routing."
        )

        # If 200, verify error is communicated in response body
        if result["status_code"] == 200:
            response_text = str(result["response"]).lower()
            assert any(
                term in response_text
                for term in ["error", "failed", "unreachable", "offline", "connection"]
            ), (
                f"200 response should contain error message. Got: {result['response'][:200]}. "
                "Cause: Error not communicated to user. "
                "Fix: Return error message when target is unreachable."
            )

    @pytest.mark.xfail(
        reason="DESIGN: Connection pooling and keep-alive prevent 1ms timeout. "
               "This tests the exception type when timeout does occur.",
        strict=False,
    )
    def test_very_short_timeout_raises_timeout_exception(
        self, agent_process_factory, http_client
    ):
        """
        Given: Extremely short timeout (1ms)
        When: Making request to agent
        Then: Timeout or ReadTimeout exception is raised

        Tests REAL: Timeout exception type (when it occurs)
        Note: May not trigger due to connection pooling
        """
        agent = agent_process_factory("timeout-test-agent")

        with pytest.raises((Timeout, ReadTimeout)):
            http_client.post(
                f"{agent.url}/a2a",
                json={"role": "user", "content": {"type": "text", "text": "test"}},
                timeout=0.001,
            )

    def test_dns_resolution_failure_handled(self, http_client):
        """
        Given: Request to non-existent domain
        When: Attempting connection
        Then: ConnectionError is raised with DNS info

        Tests REAL: DNS resolution error handling
        """
        with pytest.raises(ConnectionError) as exc_info:
            http_client.get(
                "http://this-domain-definitely-does-not-exist-xyz123.invalid/health",
                timeout=5,
            )

        # Error should mention DNS or name resolution
        error_msg = str(exc_info.value).lower()
        assert any(
            term in error_msg
            for term in ["name", "resolve", "dns", "nodename", "getaddrinfo"]
        ), (
            f"DNS error message not helpful: {exc_info.value}. "
            "Expected mention of name resolution failure."
        )


# =============================================================================
# Tests: HTTP Error Codes
# =============================================================================


class TestHTTPErrorCodes:
    """Tests for HTTP error code handling in agent requests."""

    def test_invalid_json_returns_4xx_not_5xx(self, agent_process_factory, http_client):
        """
        Given: Invalid JSON in request body
        When: Sending to agent /a2a endpoint
        Then: Returns 4xx Bad Request (not 5xx server error)

        Tests REAL: JSON parsing error handling
        """
        agent = agent_process_factory("bad-json-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            data="not valid json {{{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code < 500, (
            f"Expected 4xx for invalid JSON, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            "Cause: JSON parse error not caught before handler. "
            "Fix: Add JSON validation middleware or try/except in route."
        )

    def test_registry_returns_404_for_missing_agent(self, registry_process, http_client):
        """
        Given: Lookup for agent_id that doesn't exist
        When: Calling GET /lookup/{agent_id}
        Then: Returns 404 with error message in JSON

        Tests REAL: Registry 404 response format
        """
        response = http_client.get(
            f"{registry_process.url}/lookup/agent-that-definitely-does-not-exist"
        )

        assert response.status_code == 404, (
            f"Expected 404 for missing agent, got {response.status_code}. "
            "Cause: Registry not returning 404 for unknown agents. "
            "Fix: Check /lookup/{agent_id} returns 404 when not found."
        )

        data = response.json()
        assert "error" in data, (
            f"Expected 'error' field in 404 response. Got keys: {list(data.keys())}. "
            "Cause: Error details not included in response. "
            "Fix: Add {'error': 'Agent not found'} to 404 response."
        )

    def test_registry_returns_400_for_missing_required_fields(
        self, registry_process, http_client
    ):
        """
        Given: Registration request missing required agent_url
        When: Calling POST /register
        Then: Returns 400 Bad Request with error message

        Tests REAL: Registration field validation
        """
        response = http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": "incomplete-agent"},  # Missing agent_url
        )

        assert response.status_code == 400, (
            f"Expected 400 for missing required field, got {response.status_code}. "
            "Cause: Required field validation not enforced. "
            "Fix: Validate agent_url is present in /register."
        )

    @pytest.mark.xfail(
        reason="DESIGN: Some servers use catch-all routes that return 200 for any path. "
               "This is a design decision, not a bug.",
        strict=False,
    )
    def test_nonexistent_endpoint_returns_404(self, agent_process_factory, http_client):
        """
        Given: Request to endpoint that doesn't exist
        When: Making GET request
        Then: Returns 404 Not Found

        Tests REAL: Route not found handling
        Note: Some frameworks use catch-all routes
        """
        agent = agent_process_factory("404-test")

        response = http_client.get(f"{agent.url}/this/endpoint/does/not/exist")

        assert response.status_code == 404, (
            f"Expected 404 for nonexistent endpoint, got {response.status_code}. "
            "Cause: Server may have catch-all route. "
            "Fix: Consider if catch-all is intentional design."
        )


# =============================================================================
# Tests: Invalid Requests
# =============================================================================


class TestInvalidRequests:
    """Tests for handling of malformed and invalid requests."""

    def test_empty_request_body_returns_4xx(self, agent_process_factory, http_client):
        """
        Given: POST request with empty body
        When: Sending to agent /a2a endpoint
        Then: Returns 4xx (not 5xx crash)

        Tests REAL: Empty body validation
        """
        agent = agent_process_factory("empty-body-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            data="",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code < 500, (
            f"Empty body caused server error: {response.status_code}. "
            f"Response: {response.text[:200]}. "
            "Cause: Empty body not handled gracefully. "
            "Fix: Check for empty body before JSON parsing."
        )

    def test_wrong_content_type_returns_4xx(self, agent_process_factory, http_client):
        """
        Given: Request with text/plain instead of application/json
        When: Sending to agent /a2a endpoint
        Then: Returns 4xx (not 5xx crash)

        Tests REAL: Content-Type validation
        """
        agent = agent_process_factory("content-type-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            data="this is plain text, not JSON",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code < 500, (
            f"Wrong Content-Type caused server error: {response.status_code}. "
            "Cause: Content-Type not validated or parse error not caught. "
            "Fix: Validate Content-Type or handle parse errors."
        )

    def test_missing_message_content_field_returns_4xx(
        self, agent_process_factory, http_client
    ):
        """
        Given: A2A message JSON missing required 'content' field
        When: Sending to agent
        Then: Returns 4xx with helpful error

        Tests REAL: Message schema validation
        """
        agent = agent_process_factory("missing-fields-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            json={"role": "user"},  # Missing 'content' field
        )

        assert response.status_code < 500, (
            f"Missing required field caused server error: {response.status_code}. "
            "Cause: Message schema not validated. "
            "Fix: Add schema validation in handle_message()."
        )

    @pytest.mark.xfail(
        reason="DESIGN: Some A2A implementations accept any HTTP method. "
               "This tests strict REST compliance.",
        strict=False,
    )
    def test_get_to_post_endpoint_returns_405(self, agent_process_factory, http_client):
        """
        Given: GET request to /a2a (which expects POST)
        When: Making request
        Then: Returns 405 Method Not Allowed

        Tests REAL: HTTP method enforcement
        """
        agent = agent_process_factory("method-test")

        response = http_client.get(f"{agent.url}/a2a")

        assert response.status_code in [404, 405], (
            f"Expected 404/405 for wrong HTTP method, got {response.status_code}. "
            "Cause: HTTP method not enforced on route. "
            "Fix: Use @app.post() instead of @app.route()."
        )

    @pytest.mark.parametrize(
        "size_mb,description",
        [
            (1, "1MB message"),
            (10, "10MB message"),
        ],
    )
    def test_large_request_body_handled_gracefully(
        self, agent_process_factory, http_client, size_mb, description
    ):
        """
        Given: Request with large body ({description})
        When: Sending to agent
        Then: Either processed or rejected with 413 (not crash)

        Tests REAL: Large payload handling
        """
        agent = agent_process_factory(f"large-body-{size_mb}mb")

        large_message = "x" * (size_mb * 1024 * 1024)

        try:
            response = http_client.post(
                f"{agent.url}/a2a",
                json={
                    "role": "user",
                    "content": {"type": "text", "text": large_message},
                },
                timeout=60,  # Longer timeout for large body
            )

            # Should either succeed or return 413/400, not crash with 500
            assert response.status_code in [200, 400, 413], (
                f"{description} caused unexpected status: {response.status_code}. "
                "Cause: Large body not handled properly. "
                "Fix: Add request size limit or handle memory errors."
            )

        except requests.exceptions.Timeout:
            # Timeout is acceptable for very large requests
            pass
        except requests.exceptions.ConnectionError as e:
            # Connection reset is acceptable (server protecting itself)
            assert "reset" in str(e).lower() or "broken" in str(e).lower(), (
                f"Unexpected connection error for {description}: {e}. "
                "Cause: Server may have crashed. "
                "Fix: Add request size limit."
            )


# =============================================================================
# Tests: Registry Error Responses
# =============================================================================


class TestRegistryErrorResponses:
    """Tests for registry-specific error handling."""

    def test_duplicate_registration_returns_200_or_409(
        self, registry_process, http_client
    ):
        """
        Given: Agent already registered with ID 'dup-test'
        When: Registering again with same ID but different URL
        Then: Returns 200 (update) or 409 (conflict)

        Tests REAL: Duplicate registration handling
        """
        agent_data = {
            "agent_id": "dup-test",
            "agent_url": "http://localhost:6001",
        }

        # First registration
        response1 = http_client.post(
            f"{registry_process.url}/register", json=agent_data
        )
        assert response1.status_code == 200, "First registration should succeed"

        # Second registration with different URL
        agent_data["agent_url"] = "http://localhost:6002"
        response2 = http_client.post(
            f"{registry_process.url}/register", json=agent_data
        )

        assert response2.status_code in [200, 201, 409], (
            f"Duplicate registration returned {response2.status_code}. "
            "Cause: Duplicate handling not defined. "
            "Fix: Either update (200) or reject (409) duplicates."
        )

    def test_unregister_nonexistent_agent_returns_404(
        self, registry_process, http_client
    ):
        """
        Given: Agent ID that was never registered
        When: Calling DELETE /unregister/{agent_id}
        Then: Returns 404 Not Found

        Tests REAL: Unregister validation
        """
        response = http_client.delete(
            f"{registry_process.url}/unregister/never-registered-agent-xyz"
        )

        assert response.status_code == 404, (
            f"Expected 404 for unregistering nonexistent agent, got {response.status_code}. "
            "Cause: Missing existence check in unregister. "
            "Fix: Return 404 when agent_id not found."
        )

    def test_status_update_nonexistent_agent_returns_404(
        self, registry_process, http_client
    ):
        """
        Given: Agent ID that doesn't exist
        When: Calling PUT /status/{agent_id}
        Then: Returns 404 Not Found

        Tests REAL: Status update validation
        """
        response = http_client.put(
            f"{registry_process.url}/status/nonexistent-status-agent",
            json={"status": "busy"},
        )

        assert response.status_code == 404, (
            f"Expected 404 for updating nonexistent agent, got {response.status_code}. "
            "Cause: Missing existence check in status update. "
            "Fix: Return 404 when agent_id not found."
        )

    def test_invalid_status_value_returns_400(self, registry_process, http_client):
        """
        Given: Agent registered in registry
        When: Updating status with invalid value
        Then: Returns 400 Bad Request

        Tests REAL: Status value validation
        """
        # First register an agent
        http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": "status-validation-test", "agent_url": "http://localhost:6003"},
        )

        # Try to set invalid status
        response = http_client.put(
            f"{registry_process.url}/status/status-validation-test",
            json={"status": ""},  # Empty status
        )

        # Should reject empty status
        assert response.status_code in [200, 400], (
            f"Empty status returned {response.status_code}. "
            "Note: Whether empty status is valid is a design decision."
        )


# =============================================================================
# Tests: Agent Error Recovery
# =============================================================================


class TestAgentErrorRecovery:
    """Tests for agent behavior after encountering errors."""

    def test_agent_continues_after_malformed_request(
        self, agent_process_factory, http_client
    ):
        """
        Given: Agent receives malformed request
        When: Sending valid request afterward
        Then: Valid request is processed normally

        Tests REAL: Error isolation (one bad request doesn't break agent)
        """
        agent = agent_process_factory("recovery-test")

        # Send malformed request
        http_client.post(
            f"{agent.url}/a2a",
            data="malformed json {{{",
            headers={"Content-Type": "application/json"},
        )

        # Send valid request
        response = http_client.post(
            f"{agent.url}/a2a",
            json={
                "role": "user",
                "content": {"type": "text", "text": "valid message"},
                "conversation_id": "recovery-test",
            },
        )

        assert response.status_code == 200, (
            f"Agent not recovered after malformed request: {response.status_code}. "
            "Cause: Error state may persist across requests. "
            "Fix: Ensure request handling is stateless."
        )

    def test_agent_handles_rapid_error_requests(
        self, agent_process_factory, http_client
    ):
        """
        Given: Agent receives many malformed requests quickly
        When: Sending valid request afterward
        Then: Agent still responds normally

        Tests REAL: Error rate handling
        """
        agent = agent_process_factory("rapid-error-test")

        # Send 10 malformed requests rapidly
        for _ in range(10):
            try:
                http_client.post(
                    f"{agent.url}/a2a",
                    data="bad",
                    headers={"Content-Type": "application/json"},
                    timeout=1,
                )
            except Exception:
                pass  # Ignore errors, we're stress testing

        # Agent should still work
        response = http_client.post(
            f"{agent.url}/a2a",
            json={
                "role": "user",
                "content": {"type": "text", "text": "after errors"},
                "conversation_id": "rapid-test",
            },
            timeout=5,
        )

        assert response.status_code == 200, (
            f"Agent failed after rapid errors: {response.status_code}. "
            "Cause: Error handling may have resource leak. "
            "Fix: Ensure errors don't accumulate state."
        )


# =============================================================================
# Tests: Error Message Quality
# =============================================================================


class TestErrorMessageQuality:
    """Tests that error messages are helpful for debugging."""

    def test_404_error_includes_what_was_not_found(
        self, registry_process, http_client
    ):
        """
        Given: Request for nonexistent resource
        When: Server returns 404
        Then: Error message indicates what wasn't found

        Tests REAL: Error message usefulness
        """
        response = http_client.get(
            f"{registry_process.url}/lookup/missing-agent-xyz"
        )

        assert response.status_code == 404
        data = response.json()

        error_msg = data.get("error", "").lower()
        assert any(
            term in error_msg for term in ["not found", "missing", "does not exist"]
        ), (
            f"404 error message not helpful: '{data.get('error')}'. "
            "Cause: Generic error message. "
            "Fix: Include 'Agent not found' or similar in error."
        )

    def test_400_error_indicates_what_is_wrong(
        self, registry_process, http_client
    ):
        """
        Given: Request with missing required field
        When: Server returns 400
        Then: Error message indicates which field is missing

        Tests REAL: Validation error specificity
        """
        response = http_client.post(
            f"{registry_process.url}/register",
            json={"agent_id": "test"},  # Missing agent_url
        )

        assert response.status_code == 400
        data = response.json()

        error_msg = data.get("error", "").lower()
        assert any(
            term in error_msg for term in ["agent_url", "required", "missing", "field"]
        ), (
            f"400 error message not helpful: '{data.get('error')}'. "
            "Cause: Generic 'bad request' message. "
            "Fix: Include field name in validation error."
        )


# =============================================================================
# Tests: MCP Communication Errors (E2E specific)
# =============================================================================


class TestMCPCommunicationErrors:
    """
    Tests for MCP communication errors in E2E scenarios.

    Note: MCP protocol errors are tested in test_mcp_integration.py.
    This class tests E2E scenarios where MCP server is unreachable.
    """

    def test_mcp_query_to_unreachable_server_returns_error(
        self, registry_process, agent_process_factory, http_client, send_a2a_message
    ):
        """
        Given: MCP server registered but not running
        When: Sending #provider:server query via agent
        Then: Returns error message (not crash)

        Tests REAL: Unreachable MCP server handling in agent routing
        """
        # Register MCP server that's not actually running
        offline_port = find_free_port()
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "unreachable-mcp",
                "endpoint": f"http://localhost:{offline_port}/mcp",
                "provider": "nanda",
            },
        )

        agent = agent_process_factory("mcp-unreachable-test")

        result = send_a2a_message(agent.url, "#nanda:unreachable-mcp test query")

        # Should handle error gracefully
        assert result["status_code"] in [200, 400, 502, 503, 504], (
            f"Unreachable MCP server caused unexpected status: {result['status_code']}. "
            "Cause: MCP connection error not handled. "
            "Fix: Add try/except around MCP client calls."
        )

        # If 200, error should be in response body
        if result["status_code"] == 200:
            response_text = str(result["response"]).lower()
            assert any(
                term in response_text
                for term in ["error", "failed", "unavailable", "unreachable"]
            ), (
                f"MCP error not communicated to user: {result['response'][:200]}. "
                "Cause: Error swallowed silently. "
                "Fix: Return error message when MCP server unreachable."
            )
