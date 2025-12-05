"""
Unit tests for framework/LLM provider adapters.

Tests SimpleAgentBridge initialization and configuration.
"""

import pytest
from unittest.mock import Mock

# Import with error handling
try:
    from nanda_core.core.agent_bridge import SimpleAgentBridge
    IMPORT_SUCCESS = True
    IMPORT_ERROR = None
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.unit
class TestImportCheck:
    """Verify that all required imports work before running other tests."""

    def test_import_simple_agent_bridge(self):
        """
        Test that SimpleAgentBridge can be imported.

        This test must pass before any other tests can run.
        """
        assert IMPORT_SUCCESS, f"""
Import failed: {IMPORT_ERROR}

QUICK FIX:
  cd NEST
  pip install -e ".[dev]"
  pip install python-a2a==0.5.6
"""


@pytest.mark.unit
@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed: {IMPORT_ERROR}")
class TestSimpleAgentBridgeInitialization:
    """Tests for SimpleAgentBridge initialization and configuration."""

    def test_init_with_required_params(self, mock_agent_logic):
        """
        Test initialization with only required parameters.

        Required params: agent_id, agent_logic
        Optional params: registry_url, telemetry, mcp_registry_url, smithery_api_key
        """
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

    def test_init_with_all_params(self, mock_agent_logic, mock_telemetry):
        """
        Test initialization with all parameters.

        Verifies that optional parameters are correctly set.
        """
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
