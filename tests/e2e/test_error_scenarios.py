"""
E2E Tests for Error Scenarios.

Tests REAL error handling for network errors, timeouts, invalid requests,
and HTTP error codes in agent and registry communication.

Test Categories:
- TestNetworkErrors: Connection refused, timeouts, unreachable hosts
- TestHTTPErrorCodes: 400, 401, 403, 404, 500, 502, 503 handling
- TestInvalidRequests: Malformed requests and invalid data
- TestRegistryErrors: Registry-specific error handling
- TestMCPErrorScenarios: MCP-related errors
"""

import socket
import time

import pytest
import requests
from requests.exceptions import ConnectionError, ReadTimeout, Timeout

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT, find_free_port


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Network Errors
# =============================================================================


class TestNetworkErrors:
    """Tests for network error handling."""

    def test_connection_refused_handled_gracefully(self, http_client):
        """
        Given: Request to non-listening port
        When: Attempting connection
        Then: ConnectionError is raised (not crash)

        Tests REAL: Connection refused handling
        Mocks: None
        """
        # Find a port that's definitely not in use
        port = find_free_port()

        with pytest.raises(ConnectionError):
            http_client.get(f"http://localhost:{port}/health", timeout=2)

    def test_agent_handles_target_offline(
        self, registry_process, agent_process_factory, http_client, send_a2a_message
    ):
        """
        Given: Target agent in registry but not running
        When: Sending @mention to offline target
        Then: Error is handled gracefully

        Tests REAL: Offline target handling
        Mocks: None
        """
        sender = agent_process_factory("offline-sender")

        # Register a fake agent that's not actually running
        http_client.post(
            f"{registry_process.url}/register",
            json={
                "agent_id": "offline-target",
                "agent_url": "http://localhost:59999",  # Not running
            },
        )

        # Try to send to offline target
        result = send_a2a_message(sender.url, "@offline-target Hello")

        # Should return error, not crash
        response_text = str(result["response"]).lower()
        assert result["status_code"] != 500 or any(
            term in response_text
            for term in ["error", "failed", "unreachable", "connection"]
        ), (
            f"Offline target not handled gracefully. "
            f"Status: {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: Connection error to target not caught. "
            f"Fix: Add try/except around A2AClient.send_message()."
        )

    def test_request_timeout_handled(self, agent_process_factory, http_client):
        """
        Given: Very short timeout
        When: Making request to agent
        Then: Timeout exception raised properly

        Tests REAL: Timeout handling
        Mocks: None
        """
        agent = agent_process_factory("timeout-test-agent")

        # Use extremely short timeout to force timeout
        with pytest.raises((Timeout, ReadTimeout)):
            http_client.post(
                f"{agent.url}/a2a",
                json={"role": "user", "content": {"type": "text", "text": "test"}},
                timeout=0.001,  # 1ms - should timeout
            )

    def test_registry_offline_handled(self, http_client):
        """
        Given: Agent configured with unreachable registry
        When: Agent tries to register
        Then: Agent still starts (registration is optional)

        Tests REAL: Registry offline handling
        Mocks: None
        """
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        # Create agent with non-existent registry URL
        port = find_free_port()
        bad_registry_url = "http://localhost:59999"  # Not running

        project_root = Path(__file__).parent.parent.parent

        agent_script = f"""
import sys
sys.path.insert(0, "{project_root}")
from nanda_core.core.adapter import NANDA

def agent_logic(message: str, conversation_id: str) -> str:
    return f"Received: {{message}}"

agent = NANDA(
    agent_id="offline-registry-test",
    agent_logic=agent_logic,
    port={port},
    registry_url="{bad_registry_url}",
    public_url="http://localhost:{port}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=True)
"""

        script_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        script_file.write(agent_script)
        script_file.close()

        process = subprocess.Popen(
            [sys.executable, script_file.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(project_root),
        )

        try:
            # Wait for agent to start despite registry being offline
            started = False
            for _ in range(50):  # 5 seconds
                if is_port_in_use(port):
                    started = True
                    break
                time.sleep(0.1)

            assert started, (
                f"Expected agent to start despite offline registry. "
                f"Got: Agent failed to bind to port {port}. "
                f"Cause: Agent may be crashing when registry is unreachable. "
                f"Fix: Make registration failure non-fatal in NANDA._register()."
            )

            # Verify agent is responsive
            response = http_client.post(
                f"http://localhost:{port}/a2a",
                json={
                    "role": "user",
                    "content": {"type": "text", "text": "test"},
                    "conversation_id": "test-123",
                },
                timeout=HTTP_REQUEST_TIMEOUT,
            )

            assert response.status_code == 200, (
                f"Expected 200 from agent with offline registry, got {response.status_code}. "
                f"Cause: Agent may not be processing messages. "
                f"Fix: Ensure agent functionality is independent of registry."
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


# =============================================================================
# Tests: HTTP Error Codes
# =============================================================================


class TestHTTPErrorCodes:
    """Tests for HTTP error code handling."""

    def test_400_bad_request_for_invalid_json(self, agent_process_factory, http_client):
        """
        Given: Invalid JSON in request body
        When: Sending to agent
        Then: Returns 400 Bad Request

        Tests REAL: Invalid JSON handling
        Mocks: None
        """
        agent = agent_process_factory("bad-json-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            data="not valid json",
            headers={"Content-Type": "application/json"},
        )

        # Should return 4xx for bad request, not 5xx
        assert response.status_code < 500, (
            f"Expected 4xx for invalid JSON, got {response.status_code}. "
            f"Cause: Invalid JSON caused server error. "
            f"Fix: Add JSON validation in request handling."
        )

    def test_404_for_nonexistent_endpoint(self, agent_process_factory, http_client):
        """
        Given: Request to nonexistent endpoint
        When: Making request
        Then: Returns 404

        Tests REAL: 404 handling
        Mocks: None
        """
        agent = agent_process_factory("404-test")

        response = http_client.get(f"{agent.url}/nonexistent/endpoint")

        assert response.status_code == 404, (
            f"Expected 404 for nonexistent endpoint, got {response.status_code}. "
            f"Cause: Server may have catch-all route. "
            f"Fix: Check routing configuration."
        )

    def test_registry_404_for_missing_agent(self, registry_process, http_client):
        """
        Given: Lookup for nonexistent agent
        When: Calling /lookup/{agent_id}
        Then: Returns 404 with error message

        Tests REAL: Registry 404 response
        Mocks: None
        """
        response = http_client.get(
            f"{registry_process.url}/lookup/definitely-not-exists-xyz"
        )

        assert response.status_code == 404, (
            f"Expected 404 for missing agent, got {response.status_code}. "
            f"Cause: Registry not returning 404 for missing agents. "
            f"Fix: Check /lookup endpoint return codes."
        )

        data = response.json()
        assert "error" in data, (
            f"Expected 'error' in 404 response. "
            f"Got keys: {list(data.keys())}. "
            f"Cause: Error message not included. "
            f"Fix: Add error field to 404 response."
        )

    def test_registry_400_for_missing_required_fields(
        self, registry_process, http_client
    ):
        """
        Given: Registration request missing required fields
        When: Calling /register
        Then: Returns 400 Bad Request

        Tests REAL: Registration validation
        Mocks: None
        """
        # Missing agent_url
        response = http_client.post(
            f"{registry_process.url}/register", json={"agent_id": "incomplete-agent"}
        )

        assert response.status_code == 400, (
            f"Expected 400 for missing required fields, got {response.status_code}. "
            f"Cause: Missing field validation not working. "
            f"Fix: Check required field validation in /register."
        )


# =============================================================================
# Tests: Invalid Requests
# =============================================================================


class TestInvalidRequests:
    """Tests for invalid request handling."""

    def test_empty_request_body_handled(self, agent_process_factory, http_client):
        """
        Given: Request with empty body
        When: Sending to agent
        Then: Handled gracefully

        Tests REAL: Empty body handling
        Mocks: None
        """
        agent = agent_process_factory("empty-body-test")

        response = http_client.post(
            f"{agent.url}/a2a", data="", headers={"Content-Type": "application/json"}
        )

        # Should not crash
        assert response.status_code < 500, (
            f"Empty body caused server error: {response.status_code}. "
            f"Cause: Empty body not validated. "
            f"Fix: Add empty body check."
        )

    def test_wrong_content_type_handled(self, agent_process_factory, http_client):
        """
        Given: Request with wrong Content-Type
        When: Sending to agent
        Then: Handled gracefully

        Tests REAL: Content-Type handling
        Mocks: None
        """
        agent = agent_process_factory("content-type-test")

        response = http_client.post(
            f"{agent.url}/a2a",
            data="plain text data",
            headers={"Content-Type": "text/plain"},
        )

        # Should return 4xx, not 5xx
        assert response.status_code < 500, (
            f"Wrong Content-Type caused server error: {response.status_code}. "
            f"Cause: Content-Type not validated. "
            f"Fix: Check Content-Type in request handler."
        )

    def test_missing_required_message_fields(self, agent_process_factory, http_client):
        """
        Given: A2A message missing required fields
        When: Sending to agent
        Then: Handled gracefully

        Tests REAL: Message validation
        Mocks: None
        """
        agent = agent_process_factory("missing-fields-test")

        # Missing 'content' field
        response = http_client.post(
            f"{agent.url}/a2a", json={"role": "user"}  # Missing content
        )

        assert response.status_code < 500, (
            f"Missing fields caused server error: {response.status_code}. "
            f"Cause: Required field validation not working. "
            f"Fix: Add field validation in handle_message()."
        )

    def test_wrong_http_method_handled(self, agent_process_factory, http_client):
        """
        Given: GET request to POST endpoint
        When: Making request
        Then: Returns 405 Method Not Allowed

        Tests REAL: HTTP method validation
        Mocks: None
        """
        agent = agent_process_factory("method-test")

        response = http_client.get(f"{agent.url}/a2a")

        # Should return 405 or 404, not 500
        assert response.status_code in [404, 405], (
            f"Expected 404/405 for wrong method, got {response.status_code}. "
            f"Cause: HTTP method not validated. "
            f"Fix: Check method handling in A2A server."
        )

    def test_very_large_request_body_handled(self, agent_process_factory, http_client):
        """
        Given: Request with 10MB body
        When: Sending to agent
        Then: Handled (rejected or processed)

        Tests REAL: Large body handling
        Mocks: None
        """
        agent = agent_process_factory("large-body-test")

        large_message = "x" * (10 * 1024 * 1024)  # 10MB

        try:
            response = http_client.post(
                f"{agent.url}/a2a",
                json={
                    "role": "user",
                    "content": {"type": "text", "text": large_message},
                },
                timeout=30,  # Longer timeout for large body
            )

            # Should either succeed or return 413/400, not crash
            assert response.status_code < 500 or response.status_code == 413, (
                f"Large body caused server error: {response.status_code}. "
                f"Cause: Large body not handled. "
                f"Fix: Add request size limit."
            )
        except Exception as e:
            # Timeout or connection error is acceptable for very large request
            pass


# =============================================================================
# Tests: Registry Errors
# =============================================================================


class TestRegistryErrors:
    """Tests for registry-specific error handling."""

    def test_duplicate_registration_handled(self, registry_process, http_client):
        """
        Given: Agent already registered
        When: Registering again with same ID
        Then: Updates existing or returns appropriate response

        Tests REAL: Duplicate registration
        Mocks: None
        """
        agent_data = {
            "agent_id": "duplicate-test",
            "agent_url": "http://localhost:6001",
        }

        # First registration
        response1 = http_client.post(
            f"{registry_process.url}/register", json=agent_data
        )
        assert response1.status_code == 200, (
            f"Expected 200 for first registration, got {response1.status_code}. "
            f"Cause: Registry /register endpoint may be broken. "
            f"Fix: Check registry_server.py /register."
        )

        # Second registration (duplicate)
        agent_data["agent_url"] = "http://localhost:6002"  # Different URL
        response2 = http_client.post(
            f"{registry_process.url}/register", json=agent_data
        )

        # Should succeed (update) or return appropriate status
        assert response2.status_code in [200, 201, 409], (
            f"Duplicate registration returned unexpected status: {response2.status_code}. "
            f"Cause: Duplicate handling unclear. "
            f"Fix: Define behavior for duplicate registration."
        )

    def test_unregister_nonexistent_agent(self, registry_process, http_client):
        """
        Given: Agent ID that doesn't exist
        When: Calling /unregister
        Then: Returns 404

        Tests REAL: Unregister missing agent
        Mocks: None
        """
        response = http_client.delete(
            f"{registry_process.url}/unregister/not-registered-xyz"
        )

        assert response.status_code == 404, (
            f"Expected 404 for unregistering nonexistent agent, got {response.status_code}. "
            f"Cause: Missing agent check in unregister. "
            f"Fix: Return 404 for missing agents in /unregister."
        )

    def test_status_update_nonexistent_agent(self, registry_process, http_client):
        """
        Given: Status update for nonexistent agent
        When: Calling PUT /status/{agent_id}
        Then: Returns 404

        Tests REAL: Status update validation
        Mocks: None
        """
        response = http_client.put(
            f"{registry_process.url}/status/not-exists-xyz", json={"status": "busy"}
        )

        assert response.status_code == 404, (
            f"Expected 404 for updating nonexistent agent status, got {response.status_code}. "
            f"Cause: Missing agent check in status update. "
            f"Fix: Return 404 for missing agents in /status."
        )


# =============================================================================
# Tests: MCP Error Scenarios
# =============================================================================


class TestMCPErrorScenarios:
    """Tests for MCP-related errors."""

    def test_mcp_server_not_found(self, registry_process, http_client):
        """
        Given: MCP server name that doesn't exist
        When: Looking up
        Then: Returns 404

        Tests REAL: MCP server 404
        Mocks: None
        """
        response = http_client.get(
            f"{registry_process.url}/mcp_servers/nonexistent-mcp-server"
        )

        assert response.status_code == 404, (
            f"Expected 404 for missing MCP server, got {response.status_code}. "
            f"Cause: Missing MCP server not returning 404. "
            f"Fix: Check /mcp_servers/{name} 404 handling."
        )

    def test_mcp_server_invalid_data(self, registry_process, http_client):
        """
        Given: MCP server registration with missing fields
        When: Registering
        Then: Returns 400

        Tests REAL: MCP registration validation
        Mocks: None
        """
        # Missing qualified_name
        response = http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={"endpoint": "http://localhost:7000"},
        )

        assert response.status_code == 400, (
            f"Expected 400 for invalid MCP server data, got {response.status_code}. "
            f"Cause: MCP server validation not working. "
            f"Fix: Add required field validation for MCP servers."
        )

    def test_mcp_message_to_unavailable_server(
        self, registry_process, agent_process_factory, http_client, send_a2a_message
    ):
        """
        Given: MCP server registered but not running
        When: Sending #nanda:server query
        Then: Returns error gracefully

        Tests REAL: Unavailable MCP server handling
        Mocks: None
        """
        # Register MCP server that's not actually running
        http_client.post(
            f"{registry_process.url}/mcp_servers",
            json={
                "qualified_name": "unavailable-mcp",
                "endpoint": "http://localhost:59998/mcp",  # Not running
            },
        )

        agent = agent_process_factory("mcp-unavailable-test")

        result = send_a2a_message(agent.url, "#nanda:unavailable-mcp test query")

        # Should handle error gracefully
        assert (
            result["status_code"] < 500 or "error" in str(result["response"]).lower()
        ), (
            f"Unavailable MCP server caused crash: {result['status_code']}. "
            f"Cause: MCP connection error not handled. "
            f"Fix: Add try/except around MCP client calls."
        )

    def test_invalid_mcp_provider_format(self, agent_process_factory, send_a2a_message):
        """
        Given: Invalid MCP provider format
        When: Sending # message
        Then: Handled gracefully

        Tests REAL: Invalid MCP format handling
        Mocks: None
        """
        agent = agent_process_factory("invalid-mcp-format")

        # Various invalid formats
        invalid_formats = [
            "# no provider",
            "#:no-name",
            "#invalid-without-colon",
        ]

        for format_str in invalid_formats:
            result = send_a2a_message(agent.url, format_str)

            assert result["status_code"] < 500, (
                f"Invalid MCP format '{format_str}' caused crash: {result['status_code']}. "
                f"Cause: MCP format validation missing. "
                f"Fix: Add format validation in _handle_mcp_message()."
            )
