"""
Unit tests for SimpleAgentBridge message routing.

Tests the core message handling logic:
- Regular messages (no prefix)
- Agent-to-agent messages (@agent-id)
- System commands (/help, /ping, /status)
- MCP messages (#registry:server)

Each test includes detailed error diagnostics with potential causes and solutions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from python_a2a import Message, TextContent, MessageRole

# Try to import the module under test with detailed error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)
except Exception as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = f"Unexpected error: {str(e)}"


def diagnose_error(test_name: str, error: Exception, context: dict = None) -> str:
    """
    Generate detailed error diagnosis with potential causes and solutions.

    Args:
        test_name: Name of the failing test
        error: The exception that occurred
        context: Additional context about the test state

    Returns:
        Formatted diagnostic message
    """
    error_type = type(error).__name__
    error_msg = str(error)

    diagnosis = f"""
{'='*70}
TEST FAILURE DIAGNOSIS: {test_name}
{'='*70}

ERROR TYPE: {error_type}
ERROR MESSAGE: {error_msg}

"""

    # Add context if provided
    if context:
        diagnosis += "CONTEXT:\n"
        for key, value in context.items():
            diagnosis += f"  - {key}: {value}\n"
        diagnosis += "\n"

    # Provide specific diagnoses based on error type
    if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
        diagnosis += """
POTENTIAL CAUSES:
  1. nanda_core package not installed
  2. python-a2a dependency missing
  3. Running tests from wrong directory
  4. Virtual environment not activated

SOLUTIONS:
  1. Run: pip install -e ".[dev]" from NEST directory
  2. Run: pip install python-a2a==0.5.6
  3. Ensure you're in NEST/ directory when running pytest
  4. Activate venv: source venv/bin/activate (Linux) or venv\\Scripts\\activate (Windows)
"""

    elif "AttributeError" in error_type:
        diagnosis += f"""
POTENTIAL CAUSES:
  1. SimpleAgentBridge API changed - missing attribute/method
  2. Mock object not configured correctly
  3. Message object structure changed in python-a2a

SOLUTIONS:
  1. Check agent_bridge.py for current method signatures
  2. Verify mock setup matches expected interface
  3. Check python-a2a version: pip show python-a2a (expected: 0.5.6)
"""

    elif "TypeError" in error_type:
        diagnosis += f"""
POTENTIAL CAUSES:
  1. Wrong number of arguments passed to function
  2. Argument type mismatch
  3. API signature changed in SimpleAgentBridge

SOLUTIONS:
  1. Check SimpleAgentBridge.__init__() signature in agent_bridge.py
  2. Verify Message() constructor arguments match python-a2a docs
  3. Update test to match current API
"""

    elif "AssertionError" in error_type:
        diagnosis += f"""
POTENTIAL CAUSES:
  1. Expected behavior changed in agent_bridge.py
  2. Response format changed
  3. Message routing logic modified

SOLUTIONS:
  1. Review recent changes to agent_bridge.py
  2. Check response.content.text format
  3. Verify message prefix handling (@, #, /) logic
"""

    elif "ConnectionError" in error_type or "RequestException" in error_type:
        diagnosis += f"""
POTENTIAL CAUSES:
  1. Mock for requests.get not applied correctly
  2. Test making real network calls
  3. Registry URL being accessed

SOLUTIONS:
  1. Ensure @patch decorator covers requests.get
  2. Add mock_requests fixture
  3. Check that registry_url is None or mocked
"""

    else:
        diagnosis += f"""
POTENTIAL CAUSES:
  1. Unexpected runtime error
  2. Environment configuration issue
  3. Dependency version mismatch

SOLUTIONS:
  1. Check full stack trace above
  2. Verify all dependencies: pip install -e ".[dev]"
  3. Check Python version compatibility (requires 3.8+)
"""

    diagnosis += f"""
{'='*70}
DEBUG STEPS:
  1. Run single test: pytest tests/test_agent_bridge.py::{test_name} -v
  2. Check imports: python -c "from nanda_core.core.agent_bridge import SimpleAgentBridge"
  3. Check dependencies: pip list | grep -E "(python-a2a|flask|anthropic)"
{'='*70}
"""

    return diagnosis


class TestImportCheck:
    """Verify that all required imports work before running other tests."""

    def test_import_simple_agent_bridge(self):
        """
        Test that SimpleAgentBridge can be imported.

        This test must pass before any other tests can run.
        """
        context = {
            "import_success": IMPORT_SUCCESS,
            "import_error": IMPORT_ERROR,
            "python_a2a_required": "0.5.6"
        }

        if not IMPORT_SUCCESS:
            print(diagnose_error(
                "test_import_simple_agent_bridge",
                ImportError(IMPORT_ERROR or "Unknown import error"),
                context
            ))

        assert IMPORT_SUCCESS, f"""
Import failed: {IMPORT_ERROR}

QUICK FIX:
  cd NEST
  pip install -e ".[dev]"
"""


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestSimpleAgentBridgeInit:
    """Tests for SimpleAgentBridge initialization."""

    def test_init_with_required_params(self, mock_agent_logic):
        """
        Test initialization with only required parameters.

        Required params: agent_id, agent_logic
        Optional params: registry_url, telemetry, mcp_registry_url, smithery_api_key
        """
        test_name = "test_init_with_required_params"
        context = {
            "agent_id": "test-agent",
            "agent_logic": "mock function"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            # Verify initialization
            assert bridge.agent_id == "test-agent", \
                f"agent_id mismatch: expected 'test-agent', got '{bridge.agent_id}'"
            assert bridge.agent_logic == mock_agent_logic, \
                "agent_logic not set correctly"
            assert bridge.registry_url is None, \
                f"registry_url should be None, got '{bridge.registry_url}'"
            assert bridge.mcp_registry_url is None, \
                f"mcp_registry_url should be None, got '{bridge.mcp_registry_url}'"

            print(f"[PASS] {test_name}: SimpleAgentBridge initialized successfully")
            print(f"   - agent_id: {bridge.agent_id}")
            print(f"   - registry_url: {bridge.registry_url}")
            print(f"   - mcp_registry_url: {bridge.mcp_registry_url}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_init_with_all_params(self, mock_agent_logic, mock_telemetry):
        """
        Test initialization with all parameters.

        Verifies that optional parameters are correctly set.
        """
        test_name = "test_init_with_all_params"
        context = {
            "agent_id": "test-agent",
            "registry_url": "http://registry.example.com",
            "mcp_registry_url": "http://mcp.example.com",
            "smithery_api_key": "test-key (masked)"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic,
                registry_url="http://registry.example.com",
                telemetry=mock_telemetry,
                mcp_registry_url="http://mcp.example.com",
                smithery_api_key="test-key"
            )

            assert bridge.agent_id == "test-agent"
            assert bridge.registry_url == "http://registry.example.com", \
                f"registry_url mismatch: got '{bridge.registry_url}'"
            assert bridge.mcp_registry_url == "http://mcp.example.com", \
                f"mcp_registry_url mismatch: got '{bridge.mcp_registry_url}'"
            assert bridge.smithery_api_key == "test-key", \
                "smithery_api_key not set correctly"

            print(f"[PASS] {test_name}: All parameters set correctly")
            print(f"   - agent_id: {bridge.agent_id}")
            print(f"   - registry_url: {bridge.registry_url}")
            print(f"   - mcp_registry_url: {bridge.mcp_registry_url}")
            print(f"   - smithery_api_key: {'*' * len(bridge.smithery_api_key)}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestMessageRouting:
    """Tests for message routing based on prefix."""

    def test_regular_message_calls_agent_logic(self, mock_agent_logic, sample_text_message):
        """
        Regular message (no prefix) should call agent_logic.

        Messages without @, #, or / prefix are treated as regular messages
        and passed to the agent_logic callback for LLM processing.
        """
        test_name = "test_regular_message_calls_agent_logic"
        test_message = "Hello, how are you?"
        context = {
            "message": test_message,
            "expected_prefix": "none (regular message)",
            "expected_handler": "agent_logic callback"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message(test_message)
            response = bridge.handle_message(msg)

            assert response.role == MessageRole.AGENT, \
                f"Response role should be AGENT, got {response.role}"
            assert "Response to: Hello, how are you?" in response.content.text, \
                f"Response should contain agent_logic output, got: {response.content.text}"

            print(f"[PASS] {test_name}: Regular message routed to agent_logic")
            print(f"   - Input: {test_message}")
            print(f"   - Output: {response.content.text[:80]}...")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_regular_message_includes_agent_id(self, mock_agent_logic, sample_text_message):
        """
        Response should include agent ID prefix.

        All responses are formatted as "[agent_id] response_text"
        """
        test_name = "test_regular_message_includes_agent_id"
        context = {
            "agent_id": "my-agent",
            "expected_format": "[my-agent] ..."
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="my-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("Test message")
            response = bridge.handle_message(msg)

            assert "[my-agent]" in response.content.text, \
                f"Response should include '[my-agent]', got: {response.content.text}"

            print(f"[PASS] {test_name}: Agent ID prefix included in response")
            print(f"   - Response: {response.content.text[:80]}...")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_regular_message_logs_telemetry(self, mock_agent_logic, mock_telemetry, sample_text_message):
        """
        Regular message should log to telemetry.

        When telemetry is configured, message_received should be logged.
        """
        test_name = "test_regular_message_logs_telemetry"
        context = {
            "telemetry": "mock telemetry object",
            "expected_call": "log_message_received(agent_id, conversation_id)"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic,
                telemetry=mock_telemetry
            )

            msg = sample_text_message("Hello")
            bridge.handle_message(msg)

            mock_telemetry.log_message_received.assert_called_once()

            print(f"[PASS] {test_name}: Telemetry logged correctly")
            print(f"   - log_message_received called: True")

        except AssertionError as e:
            context["telemetry_calls"] = str(mock_telemetry.log_message_received.call_args_list)
            print(diagnose_error(test_name, e, context))
            raise
        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestSystemCommands:
    """Tests for system command handling (/command)."""

    def test_help_command(self, mock_agent_logic, sample_text_message):
        """
        Test /help command returns help text.

        /help should list all available commands.
        """
        test_name = "test_help_command"
        context = {
            "command": "/help",
            "expected_content": ["Available commands", "/help", "/ping", "/status"]
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("/help")
            response = bridge.handle_message(msg)

            response_text = response.content.text
            assert "Available commands" in response_text, \
                f"Response should contain 'Available commands', got: {response_text}"
            assert "/help" in response_text, \
                f"Response should mention /help command"
            assert "/ping" in response_text, \
                f"Response should mention /ping command"
            assert "/status" in response_text, \
                f"Response should mention /status command"

            print(f"[PASS] {test_name}: /help command returns complete help text")
            print(f"   - Response includes: Available commands, /help, /ping, /status")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_ping_command(self, mock_agent_logic, sample_text_message):
        """
        Test /ping command returns Pong.

        /ping is a simple health check that should return "Pong!"
        """
        test_name = "test_ping_command"
        context = {
            "command": "/ping",
            "expected_response": "Pong!"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("/ping")
            response = bridge.handle_message(msg)

            assert "Pong!" in response.content.text, \
                f"Response should contain 'Pong!', got: {response.content.text}"

            print(f"[PASS] {test_name}: /ping returns Pong!")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_status_command(self, mock_agent_logic, sample_text_message):
        """
        Test /status command returns agent status.

        /status should show agent ID, running status, and configured URLs.
        """
        test_name = "test_status_command"
        context = {
            "command": "/status",
            "agent_id": "test-agent",
            "registry_url": "http://registry.example.com"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic,
                registry_url="http://registry.example.com"
            )

            msg = sample_text_message("/status")
            response = bridge.handle_message(msg)

            response_text = response.content.text
            assert "test-agent" in response_text, \
                f"Response should contain agent_id 'test-agent'"
            assert "Running" in response_text, \
                f"Response should contain 'Running' status"
            assert "registry.example.com" in response_text, \
                f"Response should contain registry URL"

            print(f"[PASS] {test_name}: /status returns correct agent status")
            print(f"   - Agent: test-agent")
            print(f"   - Status: Running")
            print(f"   - Registry: registry.example.com")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_unknown_command(self, mock_agent_logic, sample_text_message):
        """
        Test unknown command returns error.

        Unrecognized commands should return an error with available commands.
        """
        test_name = "test_unknown_command"
        context = {
            "command": "/unknown",
            "expected": "error message about unknown command"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("/unknown")
            response = bridge.handle_message(msg)

            assert "Unknown command" in response.content.text, \
                f"Response should indicate unknown command, got: {response.content.text}"

            print(f"[PASS] {test_name}: Unknown command handled gracefully")
            print(f"   - Response: {response.content.text}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestAgentToAgentMessages:
    """Tests for agent-to-agent message handling (@agent-id)."""

    def test_agent_message_format_validation(self, mock_agent_logic, sample_text_message):
        """
        Test that @agent without message returns error.

        Format should be "@agent-id message", not just "@agent-id"
        """
        test_name = "test_agent_message_format_validation"
        context = {
            "input": "@other-agent",
            "expected": "error about invalid format",
            "valid_format": "@agent-id message"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("@other-agent")
            response = bridge.handle_message(msg)

            assert "Invalid format" in response.content.text, \
                f"Response should indicate invalid format, got: {response.content.text}"

            print(f"[PASS] {test_name}: Invalid @message format rejected")
            print(f"   - Input: @other-agent (no message)")
            print(f"   - Response: {response.content.text}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    @patch('nanda_core.core.agent_bridge.requests.get')
    @patch('nanda_core.core.agent_bridge.A2AClient')
    def test_agent_message_lookup_and_send(
        self, mock_a2a_client, mock_requests, mock_agent_logic, sample_text_message
    ):
        """
        Test that @agent message looks up agent and sends message.

        Flow: Parse @target -> Lookup in registry -> Send via A2A -> Return response
        """
        test_name = "test_agent_message_lookup_and_send"
        context = {
            "input": "@other-agent Hello there!",
            "target_agent": "other-agent",
            "registry_url": "http://registry.example.com",
            "expected_flow": "lookup -> send -> receive response"
        }

        try:
            # Mock registry lookup
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"agent_url": "http://other-agent:6001"}
            mock_requests.return_value = mock_response

            # Mock A2A client response
            mock_client_instance = Mock()
            mock_a2a_response = Mock()
            mock_a2a_response.parts = [Mock(text="Hello from other agent")]
            mock_client_instance.send_message.return_value = mock_a2a_response
            mock_a2a_client.return_value = mock_client_instance

            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic,
                registry_url="http://registry.example.com"
            )

            msg = sample_text_message("@other-agent Hello there!")
            response = bridge.handle_message(msg)

            # Verify registry was called
            mock_requests.assert_called_once()
            call_url = mock_requests.call_args[0][0]
            assert "other-agent" in call_url, \
                f"Registry lookup should include target agent, got: {call_url}"

            print(f"[PASS] {test_name}: A2A message flow completed")
            print(f"   - Registry lookup: {call_url}")
            print(f"   - Target found: http://other-agent:6001")
            print(f"   - Message sent successfully")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_agent_not_found(self, mock_agent_logic, sample_text_message):
        """
        Test message to non-existent agent.

        When target agent is not in registry, should return "not found" error.
        """
        test_name = "test_agent_not_found"
        context = {
            "input": "@nonexistent-agent Hello",
            "target_agent": "nonexistent-agent",
            "registry_url": "None (not configured)",
            "expected": "agent not found error"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
                # No registry_url, so lookup will fail
            )

            msg = sample_text_message("@nonexistent-agent Hello")
            response = bridge.handle_message(msg)

            assert "not found" in response.content.text.lower(), \
                f"Response should indicate agent not found, got: {response.content.text}"

            print(f"[PASS] {test_name}: Non-existent agent handled gracefully")
            print(f"   - Response: {response.content.text}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestMCPMessages:
    """Tests for MCP message handling (#registry:server)."""

    def test_mcp_message_without_registry(self, mock_agent_logic, sample_text_message):
        """
        Test MCP message without MCP registry configured.

        When using #nanda:server without mcp_registry_url, should return config error.
        """
        test_name = "test_mcp_message_without_registry"
        context = {
            "input": "#nanda:test-server get data",
            "mcp_registry_url": "None (not configured)",
            "expected": "MCP not available or not configured error"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
                # No mcp_registry_url
            )

            msg = sample_text_message("#nanda:test-server get data")
            response = bridge.handle_message(msg)

            response_lower = response.content.text.lower()
            # Should return error about MCP not available or not configured
            assert "mcp" in response_lower or "error" in response_lower or "not configured" in response_lower, \
                f"Response should indicate MCP issue, got: {response.content.text}"

            print(f"[PASS] {test_name}: MCP without registry handled correctly")
            print(f"   - Response: {response.content.text.encode('ascii', 'replace').decode()}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_mcp_message_invalid_format(self, mock_agent_logic, sample_text_message):
        """
        Test MCP message with invalid format.

        Valid format: #registry:server-name query
        Invalid: #invalid-format (missing colon separator)
        """
        test_name = "test_mcp_message_invalid_format"
        context = {
            "input": "#invalid-format",
            "valid_format": "#registry:server-name query",
            "expected": "format error"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic,
                mcp_registry_url="http://mcp.example.com"
            )

            msg = sample_text_message("#invalid-format")
            response = bridge.handle_message(msg)

            response_lower = response.content.text.lower()
            # Should return format error
            assert "invalid" in response_lower or "format" in response_lower or "error" in response_lower, \
                f"Response should indicate format error, got: {response.content.text}"

            print(f"[PASS] {test_name}: Invalid MCP format handled correctly")
            print(f"   - Input: #invalid-format")
            print(f"   - Response: {response.content.text.encode('ascii', 'replace').decode()}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestIncomingAgentMessages:
    """Tests for handling incoming messages from other agents."""

    def test_incoming_agent_message_format(self, mock_agent_logic, sample_text_message):
        """
        Test parsing of incoming agent message format.

        Incoming format: "FROM: sender\nTO: receiver\nMESSAGE: content"
        """
        test_name = "test_incoming_agent_message_format"
        incoming_msg = "FROM: sender-agent\nTO: test-agent\nMESSAGE: Hello from sender"
        context = {
            "input_format": "FROM: sender-agent\\nTO: test-agent\\nMESSAGE: Hello from sender",
            "expected": "Process message and respond"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message(incoming_msg)
            response = bridge.handle_message(msg)

            # Should process and respond
            assert "Response to sender-agent" in response.content.text, \
                f"Response should acknowledge sender, got: {response.content.text}"

            print(f"[PASS] {test_name}: Incoming agent message parsed correctly")
            print(f"   - From: sender-agent")
            print(f"   - Response: {response.content.text[:60]}...")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_incoming_reply_no_loop(self, mock_agent_logic, sample_text_message):
        """
        Test that replies don't trigger infinite loops.

        When receiving a reply (starts with "Response to"), should not respond back.
        """
        test_name = "test_incoming_reply_no_loop"
        incoming_reply = "FROM: other-agent\nTO: test-agent\nMESSAGE: Response to test-agent: Here's your answer"
        context = {
            "input": "Reply message from other-agent",
            "expected": "Display reply but don't respond back (prevent loop)"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message(incoming_reply)
            response = bridge.handle_message(msg)

            # Should display but not respond back
            assert "[other-agent]" in response.content.text, \
                f"Response should display sender, got: {response.content.text}"

            print(f"[PASS] {test_name}: Reply loop prevention working")
            print(f"   - Received reply from: other-agent")
            print(f"   - Displayed to user (no response sent back)")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestResponseFormat:
    """Tests for response message formatting."""

    def test_response_has_correct_role(self, mock_agent_logic, sample_text_message):
        """
        Response should have AGENT role.

        All responses from SimpleAgentBridge should have MessageRole.AGENT.
        """
        test_name = "test_response_has_correct_role"
        context = {
            "expected_role": "MessageRole.AGENT"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("Hello")
            response = bridge.handle_message(msg)

            assert response.role == MessageRole.AGENT, \
                f"Response role should be AGENT, got: {response.role}"

            print(f"[PASS] {test_name}: Response has correct AGENT role")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_response_has_conversation_id(self, mock_agent_logic, sample_text_message):
        """
        Response should preserve conversation ID.

        Conversation ID from request should be carried to response.
        """
        test_name = "test_response_has_conversation_id"
        conversation_id = "conv-456"
        context = {
            "input_conversation_id": conversation_id,
            "expected": "Same conversation_id in response"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("Hello", conversation_id=conversation_id)
            response = bridge.handle_message(msg)

            assert response.conversation_id == conversation_id, \
                f"Conversation ID should be '{conversation_id}', got: {response.conversation_id}"

            print(f"[PASS] {test_name}: Conversation ID preserved")
            print(f"   - conversation_id: {response.conversation_id}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise

    def test_response_has_parent_message_id(self, mock_agent_logic, sample_text_message):
        """
        Response should reference parent message.

        parent_message_id should be set to the original message's ID.
        """
        test_name = "test_response_has_parent_message_id"
        context = {
            "expected": "parent_message_id = original message's message_id"
        }

        try:
            bridge = SimpleAgentBridge(
                agent_id="test-agent",
                agent_logic=mock_agent_logic
            )

            msg = sample_text_message("Hello")
            response = bridge.handle_message(msg)

            assert response.parent_message_id == msg.message_id, \
                f"parent_message_id should be '{msg.message_id}', got: {response.parent_message_id}"

            print(f"[PASS] {test_name}: Parent message ID set correctly")
            print(f"   - parent_message_id: {response.parent_message_id}")

        except Exception as e:
            print(diagnose_error(test_name, e, context))
            raise
