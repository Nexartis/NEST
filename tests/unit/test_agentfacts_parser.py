"""
Contract Tests for AgentFacts Parsing.

Status: NOT IMPLEMENTED
The AgentFacts parser does not exist in nanda_core.
Tests raise NotImplementedError until the parser is added.

When implemented, tests should cover:
- Required field: agent_id
- Optional fields: name, description, expertise, endpoint, version
- Input validation and error handling
"""

import pytest

pytestmark = pytest.mark.unit


def _agentfacts_not_implemented():
    """Raise NotImplementedError for unimplemented AgentFacts parser."""
    raise NotImplementedError(
        "AgentFacts parser not yet implemented in nanda_core. "
        "Expected location: nanda_core/core/agentfacts.py"
    )


class TestAgentFactsParser:
    """Contract tests for AgentFacts parser - NOT IMPLEMENTED."""

    def test_parse_agent_facts_exists(self):
        """AgentFacts parser function should exist in nanda_core."""
        _agentfacts_not_implemented()

    def test_agentfacts_class_exists(self):
        """AgentFacts dataclass should exist in nanda_core."""
        _agentfacts_not_implemented()

    def test_required_field_agent_id(self):
        """Parser should require agent_id field."""
        _agentfacts_not_implemented()

    def test_optional_fields_supported(self):
        """Parser should support optional fields (name, description, etc)."""
        _agentfacts_not_implemented()

    def test_validation_errors(self):
        """Parser should raise errors for invalid input."""
        _agentfacts_not_implemented()
