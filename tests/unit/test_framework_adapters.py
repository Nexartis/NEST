"""
Unit tests for framework/LLM provider adapters.

Tests SimpleAgentBridge initialization, configuration, and validation.

SimpleAgentBridge is the main adapter that bridges LLM frameworks to A2A protocol:
- Required: agent_id, agent_logic
- Optional: registry_url, telemetry, mcp_registry_url, smithery_api_key
"""

import pytest
from unittest.mock import Mock
from python_a2a import Message, MessageRole

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

# Apply markers to all tests in this module
pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
]


# =============================================================================
# Tests: Import Verification
# =============================================================================

class TestImportVerification:
    """Verify that required imports work before running other tests."""

    def test_simple_agent_bridge_importable(self):
        """
        Given: NEST package installed
        When: Importing SimpleAgentBridge
        Then: Import succeeds without error
        """
        # This test verifies the import worked (pytestmark skipif handles failure)
        assert SimpleAgentBridge is not None, (
            "SimpleAgentBridge should be importable. "
            "Cause: Package not installed or dependency missing. "
            "Fix: Run 'pip install -e .[dev]' and 'pip install python-a2a==0.5.6'"
        )


# =============================================================================
# Tests: Required Parameters
# =============================================================================

class TestRequiredParameters:
    """Tests for required parameter validation."""

    def test_init_requires_agent_id_and_agent_logic(self, mock_agent_logic):
        """
        Given: Required params (agent_id, agent_logic)
        When: Creating SimpleAgentBridge
        Then: Initializes successfully with both params stored
        """
        bridge = SimpleAgentBridge(
            agent_id="test-agent",
            agent_logic=mock_agent_logic
        )

        assert bridge.agent_id == "test-agent", (
            f"Expected agent_id='test-agent', got '{bridge.agent_id}'. "
            f"Cause: agent_id not stored in __init__. "
            f"Fix: Add self.agent_id = agent_id"
        )
        assert bridge.agent_logic == mock_agent_logic, (
            "agent_logic not stored correctly. "
            "Cause: agent_logic not assigned. "
            "Fix: Add self.agent_logic = agent_logic"
        )

    def test_agent_logic_is_callable(self, mock_agent_logic):
        """
        Given: A callable agent_logic function
        When: Calling agent_logic through bridge
        Then: Returns expected result without error
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic
        )

        result = bridge.agent_logic("test message", "conv-id")

        assert result is not None, (
            "agent_logic should return a result. "
            "Cause: Mock not configured correctly or agent_logic not callable. "
            "Fix: Verify agent_logic is a callable"
        )


# =============================================================================
# Tests: Optional Parameters - Defaults
# =============================================================================

class TestOptionalParameterDefaults:
    """Tests for optional parameter default values."""

    def test_registry_url_defaults_to_none(self, mock_agent_logic):
        """
        Given: No registry_url provided
        When: Creating bridge
        Then: registry_url is None
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_agent_logic)

        assert bridge.registry_url is None, (
            f"Expected registry_url=None, got '{bridge.registry_url}'. "
            f"Cause: Default value changed. "
            f"Fix: Set registry_url=None in __init__ signature"
        )

    def test_mcp_registry_url_defaults_to_none(self, mock_agent_logic):
        """
        Given: No mcp_registry_url provided
        When: Creating bridge
        Then: mcp_registry_url is None
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_agent_logic)

        assert bridge.mcp_registry_url is None, (
            f"Expected mcp_registry_url=None, got '{bridge.mcp_registry_url}'. "
            f"Cause: Default value changed. "
            f"Fix: Set mcp_registry_url=None in __init__ signature"
        )

    def test_smithery_api_key_defaults_to_none(self, mock_agent_logic):
        """
        Given: No smithery_api_key provided
        When: Creating bridge
        Then: smithery_api_key is None
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_agent_logic)

        assert bridge.smithery_api_key is None, (
            f"Expected smithery_api_key=None, got '{bridge.smithery_api_key}'. "
            f"Cause: Default value changed. "
            f"Fix: Set smithery_api_key=None in __init__ signature"
        )

    def test_telemetry_defaults_to_none(self, mock_agent_logic):
        """
        Given: No telemetry provided
        When: Creating bridge
        Then: telemetry is None
        """
        bridge = SimpleAgentBridge(agent_id="test", agent_logic=mock_agent_logic)

        assert bridge.telemetry is None, (
            f"Expected telemetry=None, got '{bridge.telemetry}'. "
            f"Cause: Default value changed. "
            f"Fix: Set telemetry=None in __init__ signature"
        )


# =============================================================================
# Tests: Optional Parameters - Custom Values
# =============================================================================

class TestOptionalParameterValues:
    """Tests for optional parameter custom values."""

    def test_registry_url_stores_custom_value(self, mock_agent_logic):
        """
        Given: registry_url="http://registry.example.com"
        When: Creating bridge
        Then: registry_url is stored and accessible
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com"
        )

        assert bridge.registry_url == "http://registry.example.com", (
            f"Expected 'http://registry.example.com', got '{bridge.registry_url}'. "
            f"Cause: registry_url not stored. "
            f"Fix: Add self.registry_url = registry_url"
        )

    def test_mcp_registry_url_stores_custom_value(self, mock_agent_logic):
        """
        Given: mcp_registry_url="http://mcp.example.com"
        When: Creating bridge
        Then: mcp_registry_url is stored and accessible
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            mcp_registry_url="http://mcp.example.com"
        )

        assert bridge.mcp_registry_url == "http://mcp.example.com", (
            f"Expected 'http://mcp.example.com', got '{bridge.mcp_registry_url}'. "
            f"Cause: mcp_registry_url not stored. "
            f"Fix: Add self.mcp_registry_url = mcp_registry_url"
        )

    def test_smithery_api_key_stores_custom_value(self, mock_agent_logic):
        """
        Given: smithery_api_key="secret-key-123"
        When: Creating bridge
        Then: smithery_api_key is stored and accessible
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            smithery_api_key="secret-key-123"
        )

        assert bridge.smithery_api_key == "secret-key-123", (
            f"Expected 'secret-key-123', got '{bridge.smithery_api_key}'. "
            f"Cause: smithery_api_key not stored. "
            f"Fix: Add self.smithery_api_key = smithery_api_key"
        )

    def test_telemetry_stores_custom_value(self, mock_agent_logic, mock_telemetry):
        """
        Given: telemetry object provided
        When: Creating bridge
        Then: telemetry is stored and accessible
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            telemetry=mock_telemetry
        )

        assert bridge.telemetry == mock_telemetry, (
            "telemetry not stored correctly. "
            "Cause: telemetry not assigned. "
            "Fix: Add self.telemetry = telemetry"
        )


# =============================================================================
# Tests: Full Configuration
# =============================================================================

class TestFullConfiguration:
    """Tests for bridge with all parameters configured."""

    def test_init_with_all_params(self, mock_agent_logic, mock_telemetry):
        """
        Given: All parameters provided
        When: Creating bridge
        Then: All parameters are correctly stored
        """
        bridge = SimpleAgentBridge(
            agent_id="full-config-agent",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com",
            telemetry=mock_telemetry,
            mcp_registry_url="http://mcp.example.com",
            smithery_api_key="api-key-xyz"
        )

        assert bridge.agent_id == "full-config-agent", "agent_id mismatch"
        assert bridge.registry_url == "http://registry.example.com", "registry_url mismatch"
        assert bridge.mcp_registry_url == "http://mcp.example.com", "mcp_registry_url mismatch"
        assert bridge.smithery_api_key == "api-key-xyz", "smithery_api_key mismatch"
        assert bridge.telemetry == mock_telemetry, "telemetry mismatch"

    def test_fully_configured_bridge_handles_message(self, mock_agent_logic, sample_text_message):
        """
        Given: Fully configured bridge
        When: Processing a message
        Then: Returns valid Message with AGENT role
        """
        bridge = SimpleAgentBridge(
            agent_id="functional-test",
            agent_logic=mock_agent_logic,
            registry_url="http://registry.example.com"
        )

        response = bridge.handle_message(sample_text_message("Hello"))

        assert isinstance(response, Message), (
            f"Expected Message, got {type(response).__name__}. "
            f"Cause: handle_message not returning Message. "
            f"Fix: Check return type in handle_message()"
        )
        assert response.role == MessageRole.AGENT, (
            f"Expected AGENT role, got {response.role}. "
            f"Cause: Role assignment wrong. "
            f"Fix: Set role=MessageRole.AGENT in _create_response()"
        )


# =============================================================================
# Tests: Agent ID Format Variations
# =============================================================================

class TestAgentIdFormats:
    """Tests for different agent_id formats using parameterization."""

    @pytest.mark.parametrize("agent_id", [
        "simple",
        "with-hyphens",
        "with_underscores",
        "agent123",
        "UPPERCASE",
        "MixedCase",
        "data-analyst_v2.1",
    ])
    def test_agent_id_formats_preserved(self, mock_agent_logic, agent_id):
        """
        Given: Various agent_id formats (simple, hyphenated, underscored, numeric, mixed)
        When: Creating bridge
        Then: agent_id is stored exactly as provided (no sanitization)
        """
        bridge = SimpleAgentBridge(agent_id=agent_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == agent_id, (
            f"Expected '{agent_id}', got '{bridge.agent_id}'. "
            f"Cause: agent_id was modified/sanitized. "
            f"Fix: Store agent_id as-is without transformation"
        )


# =============================================================================
# Tests: URL Format Variations
# =============================================================================

class TestUrlFormats:
    """Tests for different URL formats."""

    @pytest.mark.parametrize("url,description", [
        ("http://localhost", "localhost without port"),
        ("http://localhost:8080", "localhost with port"),
        ("https://secure.example.com", "HTTPS URL"),
        ("http://example.com/api/v1", "URL with path"),
        ("http://example.com:9999/api/v1/registry", "URL with port and path"),
    ])
    def test_registry_url_formats_preserved(self, mock_agent_logic, url, description):
        """
        Given: Various URL formats (localhost, with port, HTTPS, with path)
        When: Creating bridge with registry_url
        Then: URL is stored exactly as provided
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url=url
        )

        assert bridge.registry_url == url, (
            f"URL not preserved for {description}. "
            f"Expected '{url}', got '{bridge.registry_url}'. "
            f"Cause: URL was modified. "
            f"Fix: Store registry_url as-is"
        )


# =============================================================================
# Tests: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_agent_id(self, mock_agent_logic):
        """
        Given: agent_id="" (empty string)
        When: Creating bridge
        Then: Empty string is stored (no validation enforced)
        """
        bridge = SimpleAgentBridge(agent_id="", agent_logic=mock_agent_logic)

        assert bridge.agent_id == "", (
            f"Expected empty string, got '{bridge.agent_id}'. "
            f"Cause: Empty string rejected or modified. "
            f"Fix: Allow empty agent_id if no validation required"
        )

    def test_very_long_agent_id(self, mock_agent_logic):
        """
        Given: agent_id with 200 characters
        When: Creating bridge
        Then: Long agent_id is stored without truncation
        """
        long_id = "agent-" + "x" * 194  # 200 chars total
        bridge = SimpleAgentBridge(agent_id=long_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == long_id, (
            f"Expected 200-char agent_id, got {len(bridge.agent_id)} chars. "
            f"Cause: agent_id was truncated. "
            f"Fix: Remove length restriction on agent_id"
        )
        assert len(bridge.agent_id) == 200, (
            f"Expected 200 chars, got {len(bridge.agent_id)}. "
            f"Cause: Length truncation. "
            f"Fix: Store full agent_id"
        )

    def test_empty_string_registry_url(self, mock_agent_logic):
        """
        Given: registry_url="" (empty string)
        When: Creating bridge
        Then: Empty string is stored
        """
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            registry_url=""
        )

        assert bridge.registry_url == "", (
            f"Expected empty string, got '{bridge.registry_url}'. "
            f"Cause: Empty string converted to None. "
            f"Fix: Don't convert empty string to None"
        )

    def test_whitespace_only_agent_id(self, mock_agent_logic):
        """
        Given: agent_id="   " (whitespace only)
        When: Creating bridge
        Then: Whitespace is stored (no stripping)
        """
        bridge = SimpleAgentBridge(agent_id="   ", agent_logic=mock_agent_logic)

        assert bridge.agent_id == "   ", (
            f"Expected '   ', got '{bridge.agent_id}'. "
            f"Cause: Whitespace stripped. "
            f"Fix: Don't strip agent_id"
        )

    def test_unicode_in_agent_id(self, mock_agent_logic):
        """
        Given: agent_id with unicode "agent-\u4e2d\u6587"
        When: Creating bridge
        Then: Unicode is preserved
        """
        unicode_id = "agent-\u4e2d\u6587"
        bridge = SimpleAgentBridge(agent_id=unicode_id, agent_logic=mock_agent_logic)

        assert bridge.agent_id == unicode_id, (
            f"Expected '{unicode_id}', got '{bridge.agent_id}'. "
            f"Cause: Unicode not handled correctly. "
            f"Fix: Ensure UTF-8 support in agent_id storage"
        )

    def test_special_chars_in_smithery_api_key(self, mock_agent_logic):
        """
        Given: smithery_api_key with special characters
        When: Creating bridge
        Then: Special characters are preserved
        """
        special_key = "key_with-special.chars!@#$%"
        bridge = SimpleAgentBridge(
            agent_id="test",
            agent_logic=mock_agent_logic,
            smithery_api_key=special_key
        )

        assert bridge.smithery_api_key == special_key, (
            f"Expected '{special_key}', got '{bridge.smithery_api_key}'. "
            f"Cause: Special characters escaped or removed. "
            f"Fix: Store API key as-is without escaping"
        )
