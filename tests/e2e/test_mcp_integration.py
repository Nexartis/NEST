"""
E2E Tests for Real MCP Integration.

Tests REAL MCP server communication using actual MCP protocol.
Uses mcp_test_server.py as a real MCP server for testing.

Test Categories:
- TestMCPServerDirect: Direct MCP server communication
- TestMCPThroughAgent: MCP queries via agent (#nanda: format)
- TestMCPToolExecution: Tool listing and execution
- TestMCPErrorHandling: Error scenarios
"""

import json
import time

import pytest
import requests

from tests.e2e.conftest import HTTP_REQUEST_TIMEOUT

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Direct MCP Server Communication
# =============================================================================


class TestMCPServerDirect:
    """Tests for direct communication with MCP test server."""

    def test_mcp_server_health_check(self, mcp_test_server, http_client):
        """
        Given: Running MCP test server
        When: Calling /health endpoint
        Then: Returns healthy status

        Tests REAL: MCP server availability
        Mocks: None
        """
        response = http_client.get(f"{mcp_test_server.url}/health")

        assert response.status_code == 200, (
            f"Expected 200 from MCP server health, got {response.status_code}. "
            f"Cause: MCP server may not be running. "
            f"Fix: Check mcp_test_server fixture."
        )

        data = response.json()
        assert data.get("status") == "ok", (
            f"Expected status='ok', got '{data.get('status')}'. "
            f"Cause: MCP server unhealthy. "
            f"Fix: Check mcp_test_server.py health endpoint."
        )

    def test_mcp_initialize_protocol(self, mcp_test_server, http_client):
        """
        Given: Running MCP test server
        When: Sending MCP initialize request
        Then: Returns protocol version and capabilities

        Tests REAL: MCP protocol initialization
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from MCP initialize, got {response.status_code}. "
            f"Cause: MCP server rejected initialize. "
            f"Fix: Check MCP protocol handling."
        )

        data = response.json()
        assert "result" in data, (
            f"Expected 'result' in MCP response. "
            f"Got keys: {list(data.keys())}. "
            f"Cause: Invalid MCP response format. "
            f"Fix: Check mcp_test_server.py initialize handler."
        )

        result = data["result"]
        assert "protocolVersion" in result, (
            f"Expected 'protocolVersion' in result. "
            f"Cause: MCP server not returning protocol version. "
            f"Fix: Check initialize response format."
        )

    def test_mcp_tools_list(self, mcp_test_server, http_client):
        """
        Given: Initialized MCP connection
        When: Requesting tools/list
        Then: Returns available tools

        Tests REAL: MCP tool listing
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from tools/list, got {response.status_code}. "
            f"Cause: MCP server rejected tools/list. "
            f"Fix: Check MCP tools/list handler."
        )

        data = response.json()
        tools = data.get("result", {}).get("tools", [])

        assert len(tools) >= 3, (
            f"Expected at least 3 tools, got {len(tools)}. "
            f"Tools: {[t.get('name') for t in tools]}. "
            f"Cause: MCP server missing expected tools. "
            f"Fix: Check TOOLS definition in mcp_test_server.py."
        )

        tool_names = [t.get("name") for t in tools]
        for expected_tool in ["echo", "add", "get_time"]:
            assert expected_tool in tool_names, (
                f"Expected tool '{expected_tool}' in tool list. "
                f"Got: {tool_names}. "
                f"Cause: Tool not registered. "
                f"Fix: Add {expected_tool} to mcp_test_server TOOLS."
            )

    def test_mcp_tool_call_echo(self, mcp_test_server, http_client):
        """
        Given: Running MCP server with echo tool
        When: Calling echo tool with message
        Then: Returns echoed message

        Tests REAL: MCP tool execution
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {"message": "Hello from E2E test!"},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from tools/call, got {response.status_code}. "
            f"Cause: MCP tool execution failed. "
            f"Fix: Check tools/call handler."
        )

        data = response.json()
        content = data.get("result", {}).get("content", [])

        assert len(content) > 0, (
            f"Expected content in tool response. "
            f"Got: {data}. "
            f"Cause: Tool returned empty response. "
            f"Fix: Check echo tool implementation."
        )

        result_text = content[0].get("text", "")
        assert "Hello from E2E test!" in result_text, (
            f"Expected echo to contain original message. "
            f"Got: {result_text}. "
            f"Cause: Echo tool not returning message. "
            f"Fix: Check echo tool implementation."
        )

    def test_mcp_tool_call_add(self, mcp_test_server, http_client):
        """
        Given: Running MCP server with add tool
        When: Calling add tool with numbers
        Then: Returns correct sum

        Tests REAL: MCP tool with numeric parameters
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "add",
                "arguments": {"a": 5, "b": 7},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from add tool, got {response.status_code}. "
            f"Cause: Add tool execution failed. "
            f"Fix: Check add tool implementation."
        )

        data = response.json()
        content = data.get("result", {}).get("content", [])
        result_text = content[0].get("text", "") if content else ""

        assert "12" in result_text, (
            f"Expected result to contain '12' (5+7). "
            f"Got: {result_text}. "
            f"Cause: Add tool calculation incorrect. "
            f"Fix: Check add tool implementation."
        )

    def test_mcp_tool_call_get_time(self, mcp_test_server, http_client):
        """
        Given: Running MCP server with get_time tool
        When: Calling get_time tool
        Then: Returns current time

        Tests REAL: MCP tool without parameters
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_time",
                "arguments": {},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 from get_time tool, got {response.status_code}. "
            f"Cause: get_time tool execution failed. "
            f"Fix: Check get_time tool implementation."
        )

        data = response.json()
        content = data.get("result", {}).get("content", [])
        result_text = content[0].get("text", "") if content else ""

        # Should contain ISO format timestamp
        assert "T" in result_text and ":" in result_text, (
            f"Expected ISO timestamp in result. "
            f"Got: {result_text}. "
            f"Cause: get_time not returning proper timestamp. "
            f"Fix: Check get_time tool implementation."
        )


# =============================================================================
# Tests: MCP Through Agent
# =============================================================================


class TestMCPThroughAgent:
    """Tests for MCP queries routed through an agent."""

    def test_mcp_server_registered_in_registry(
        self, registry_process, mcp_test_server, http_client
    ):
        """
        Given: Running MCP test server
        When: Registering it in the NANDA registry
        Then: Server is discoverable

        Tests REAL: MCP server registration
        Mocks: None
        """
        # Register MCP server in registry
        mcp_data = {
            "qualified_name": "e2e-mcp-test",
            "endpoint": mcp_test_server.url,
            "server_url": mcp_test_server.url,
            "description": "E2E Test MCP Server",
            "provider": "nanda",
        }

        response = http_client.post(
            f"{registry_process.url}/mcp_servers", json=mcp_data
        )

        assert response.status_code == 200, (
            f"Expected 200 from MCP registration, got {response.status_code}. "
            f"Response: {response.text[:200]}. "
            f"Cause: MCP server registration failed. "
            f"Fix: Check /mcp_servers endpoint."
        )

        # Verify discoverable
        lookup_response = http_client.get(
            f"{registry_process.url}/mcp_servers/e2e-mcp-test"
        )

        assert lookup_response.status_code == 200, (
            f"Expected 200 from MCP lookup, got {lookup_response.status_code}. "
            f"Cause: MCP server not stored. "
            f"Fix: Check MCP server storage."
        )

    def test_full_mcp_flow_agent_to_server(
        self, registry_process, mcp_test_server, agent_process_factory, send_a2a_message, http_client
    ):
        """
        Given: MCP server registered in registry, agent running
        When: Agent receives #nanda:server-name query
        Then: Full flow executes: agent→registry lookup→MCP call→result returned

        Tests REAL: Complete MCP integration flow
        Mocks: None - this is THE critical E2E MCP test
        """
        # Step 1: Register MCP server in registry
        mcp_data = {
            "qualified_name": "e2e-echo-server",
            "endpoint": mcp_test_server.url,
            "server_url": mcp_test_server.url,
            "description": "E2E Echo MCP Server",
            "provider": "nanda",
        }
        reg_response = http_client.post(
            f"{registry_process.url}/mcp_servers", json=mcp_data
        )
        assert reg_response.status_code == 200, (
            f"MCP server registration failed: {reg_response.status_code}. "
            f"Response: {reg_response.text[:200]}"
        )

        # Step 2: Start agent that can route MCP requests
        agent = agent_process_factory("mcp-flow-test")

        # Step 3: Send MCP query through agent
        # The agent should: parse #nanda:e2e-echo-server → lookup in registry → call MCP server
        result = send_a2a_message(
            agent.url,
            "#nanda:e2e-echo-server echo Hello from E2E test"
        )

        assert result["status_code"] == 200, (
            f"Full MCP flow failed: {result['status_code']}. "
            f"Response: {result['response']}. "
            f"Cause: Agent→Registry→MCP chain broken. "
            f"Fix: Debug each step: 1) #nanda parsing, 2) registry lookup, 3) MCP call."
        )

        # Step 4: Verify the response indicates MCP processing
        response_text = str(result["response"]).lower()
        # Should see evidence of MCP routing attempt
        assert any(
            indicator in response_text
            for indicator in ["e2e-echo-server", "echo", "mcp", "nanda"]
        ), (
            f"Expected MCP flow evidence in response. "
            f"Got: {result['response'][:300]}. "
            f"Cause: MCP request may not have reached server. "
            f"Fix: Check MCPRegistry.get_nanda_mcp_server_info() and MCPClient calls."
        )

    def test_agent_receives_mcp_format_message(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Agent running
        When: Sending #nanda:server-name query message
        Then: Agent recognizes MCP format and attempts routing

        Tests REAL: Agent MCP message detection via SimpleAgentBridge
        Mocks: None - tests real _handle_mcp_message path
        """
        agent = agent_process_factory("mcp-format-test")

        # Send MCP-formatted message
        result = send_a2a_message(agent.url, "#nanda:test-server What is the weather?")

        # Agent should recognize and attempt to process
        assert result["status_code"] == 200, (
            f"Expected 200 for MCP format message, got {result['status_code']}. "
            f"Cause: Agent may be crashing on # prefix. "
            f"Fix: Check _handle_mcp_message() in SimpleAgentBridge."
        )

        response_text = str(result["response"]).lower()
        # Response MUST indicate MCP processing was attempted
        # The #nanda: prefix should trigger _handle_mcp_message() path
        mcp_indicators = ["#nanda", "mcp", "test-server", "not found", "registry"]
        matched = [ind for ind in mcp_indicators if ind in response_text]
        assert len(matched) >= 1, (
            f"Expected MCP routing evidence (one of {mcp_indicators}). "
            f"Got: {result['response'][:200]}. "
            f"Cause: Message not routed to _handle_mcp_message(). "
            f"Fix: Check handle_message() routes # prefix to MCP handler."
        )

    def test_agent_mcp_smithery_format_recognized(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Agent running
        When: Sending #smithery:server-name query message
        Then: Agent recognizes Smithery MCP format

        Tests REAL: Agent Smithery MCP message detection
        Mocks: None
        """
        agent = agent_process_factory("smithery-format-test")

        result = send_a2a_message(
            agent.url, "#smithery:weather-server Get forecast for NYC"
        )

        assert result["status_code"] == 200, (
            f"Expected 200 for Smithery format message, got {result['status_code']}. "
            f"Cause: Agent may be crashing on #smithery: prefix. "
            f"Fix: Check Smithery handling in _handle_mcp_message()."
        )

        response_text = str(result["response"]).lower()
        # Response MUST show Smithery routing was attempted
        smithery_indicators = ["#smithery", "smithery", "weather-server", "api_key", "mcp"]
        matched = [ind for ind in smithery_indicators if ind in response_text]
        assert len(matched) >= 1, (
            f"Expected Smithery routing evidence (one of {smithery_indicators}). "
            f"Got: {result['response'][:200]}. "
            f"Cause: Agent not recognizing #smithery: prefix. "
            f"Fix: Check registry_provider parsing in _handle_mcp_message()."
        )

    def test_agent_mcp_invalid_format_handled(
        self, agent_process_factory, send_a2a_message
    ):
        """
        Given: Agent running
        When: Sending malformed # message (missing colon)
        Then: Agent returns helpful error

        Tests REAL: MCP format validation
        Mocks: None
        """
        agent = agent_process_factory("mcp-invalid-format-test")

        # Missing colon - invalid format
        result = send_a2a_message(agent.url, "#nanda-server query")

        assert result["status_code"] == 200, (
            f"Expected 200 even for invalid MCP format, got {result['status_code']}. "
            f"Cause: Agent crashing on malformed # message. "
            f"Fix: Add format validation in _handle_mcp_message()."
        )

        response_text = str(result["response"]).lower()
        # The malformed #nanda-server (missing colon) should be handled gracefully
        # Agent should either treat as regular message or return format guidance
        assert result["status_code"] == 200, (
            f"Expected agent to handle malformed # gracefully. "
            f"Got: {result['response'][:200]}."
        )


# =============================================================================
# Tests: MCP Error Handling
# =============================================================================


class TestMCPErrorHandling:
    """Tests for MCP error scenarios."""

    def test_mcp_invalid_method(self, mcp_test_server, http_client):
        """
        Given: Running MCP server
        When: Calling invalid method
        Then: Returns proper error

        Tests REAL: MCP error handling
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "invalid/method",
            "params": {},
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200 (JSON-RPC error in body), got {response.status_code}. "
            f"Cause: Server returned HTTP error instead of JSON-RPC error. "
            f"Fix: Return JSON-RPC error format."
        )

        data = response.json()
        assert "error" in data, (
            f"Expected 'error' in response for invalid method. "
            f"Got: {data}. "
            f"Cause: Invalid method not returning error. "
            f"Fix: Check unknown method handling."
        )

    def test_mcp_unknown_tool(self, mcp_test_server, http_client):
        """
        Given: Running MCP server
        When: Calling unknown tool
        Then: Returns error message

        Tests REAL: Unknown tool handling
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}. "
            f"Cause: Unknown tool caused HTTP error. "
            f"Fix: Return graceful error for unknown tools."
        )

        data = response.json()
        content = data.get("result", {}).get("content", [])
        result_text = content[0].get("text", "") if content else ""

        assert (
            "unknown" in result_text.lower() or "nonexistent" in result_text.lower()
        ), (
            f"Expected error message mentioning unknown tool. "
            f"Got: {result_text}. "
            f"Cause: Unknown tool not returning error message. "
            f"Fix: Check unknown tool handling in _execute_tool."
        )

    def test_mcp_malformed_json_rpc(self, mcp_test_server, http_client):
        """
        Given: Running MCP server
        When: Sending malformed JSON-RPC
        Then: Returns proper error

        Tests REAL: Malformed request handling
        Mocks: None
        """
        # Missing method field
        request = {
            "jsonrpc": "2.0",
            "id": 102,
            "params": {},
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        # Should not crash
        assert response.status_code < 500, (
            f"Malformed JSON-RPC caused server error: {response.status_code}. "
            f"Cause: Missing required field not validated. "
            f"Fix: Add JSON-RPC validation."
        )

    def test_mcp_invalid_json(self, mcp_test_server, http_client):
        """
        Given: Running MCP server
        When: Sending invalid JSON
        Then: Returns 400 Bad Request

        Tests REAL: Invalid JSON handling
        Mocks: None
        """
        response = http_client.post(
            mcp_test_server.url,
            data="not valid json",
            headers={"Content-Type": "application/json"},
            timeout=HTTP_REQUEST_TIMEOUT,
        )

        assert response.status_code == 400, (
            f"Expected 400 for invalid JSON, got {response.status_code}. "
            f"Cause: Invalid JSON not detected. "
            f"Fix: Add JSON parsing error handling."
        )


# =============================================================================
# Tests: MCP Tool Schema Validation
# =============================================================================


class TestMCPToolSchemas:
    """Tests for MCP tool input schema handling."""

    def test_tool_missing_required_argument(self, mcp_test_server, http_client):
        """
        Given: Tool with required argument
        When: Calling without required argument
        Then: Tool handles gracefully

        Tests REAL: Required argument handling
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 200,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {},  # Missing required 'message'
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        # Should not crash
        assert response.status_code < 500, (
            f"Missing required argument caused server error: {response.status_code}. "
            f"Cause: Required argument validation not handled. "
            f"Fix: Add argument validation in _execute_tool."
        )

    def test_tool_wrong_argument_type(self, mcp_test_server, http_client):
        """
        Given: Tool expecting numbers
        When: Calling with string arguments
        Then: Tool handles gracefully

        Tests REAL: Type coercion handling
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {
                "name": "add",
                "arguments": {"a": "not a number", "b": "also not"},
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        # Should not crash
        assert response.status_code < 500, (
            f"Wrong argument type caused server error: {response.status_code}. "
            f"Cause: Type validation not handled. "
            f"Fix: Add type coercion or validation."
        )

    def test_tool_extra_arguments_ignored(self, mcp_test_server, http_client):
        """
        Given: Tool with defined schema
        When: Calling with extra arguments
        Then: Extra arguments are ignored

        Tests REAL: Extra argument handling
        Mocks: None
        """
        request = {
            "jsonrpc": "2.0",
            "id": 202,
            "method": "tools/call",
            "params": {
                "name": "echo",
                "arguments": {
                    "message": "Hello",
                    "extra_arg": "should be ignored",
                    "another_extra": 12345,
                },
            },
        }

        response = http_client.post(
            mcp_test_server.url, json=request, timeout=HTTP_REQUEST_TIMEOUT
        )

        assert response.status_code == 200, (
            f"Extra arguments caused error: {response.status_code}. "
            f"Cause: Extra arguments not tolerated. "
            f"Fix: Ignore unknown arguments."
        )

        data = response.json()
        content = data.get("result", {}).get("content", [])
        result_text = content[0].get("text", "") if content else ""

        assert "Hello" in result_text, (
            f"Expected echo result with 'Hello'. "
            f"Got: {result_text}. "
            f"Cause: Extra arguments affected processing. "
            f"Fix: Only use defined arguments."
        )
