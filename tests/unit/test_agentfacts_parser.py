"""
Unit tests for AgentFacts parsing and validation.

AgentFacts represent standardized metadata about an agent:
- Identity: agent_id (required), name (optional)
- Capabilities: expertise list, skills
- Contact: endpoint URL
- Version: semantic version string

Note: These tests define the expected contract for AgentFacts parsing.
The reference implementation below will be replaced when the production
parser is implemented in nanda_core.
"""

import pytest
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# =============================================================================
# Reference Implementation (to be replaced by production code)
# =============================================================================

@dataclass
class AgentFacts:
    """
    Agent metadata structure.

    Required fields:
        agent_id: Unique identifier for the agent

    Optional fields:
        name: Human-readable display name
        description: What the agent does
        expertise: List of capabilities/skills
        endpoint: URL to reach the agent
        version: Semantic version string
    """
    agent_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    expertise: Optional[List[str]] = None
    endpoint: Optional[str] = None
    version: Optional[str] = None


class AgentFactsParseError(ValueError):
    """Raised when AgentFacts parsing fails."""
    pass


def parse_agent_facts(data: Any) -> AgentFacts:
    """
    Parse dictionary into AgentFacts.

    Args:
        data: Dictionary containing agent metadata

    Returns:
        AgentFacts object

    Raises:
        AgentFactsParseError: If data is invalid or missing required fields
    """
    # Type validation
    if data is None:
        raise AgentFactsParseError("Input cannot be None")
    if not isinstance(data, dict):
        raise AgentFactsParseError(
            f"Expected dict, got {type(data).__name__}. "
            "AgentFacts must be a JSON object."
        )

    # Required field: agent_id
    if "agent_id" not in data:
        raise AgentFactsParseError(
            "Missing required field: agent_id. "
            "Every agent must have a unique identifier."
        )

    agent_id = data["agent_id"]
    if not isinstance(agent_id, str):
        raise AgentFactsParseError(
            f"agent_id must be a string, got {type(agent_id).__name__}. "
            "Example: 'my-agent-v1'"
        )
    if not agent_id.strip():
        raise AgentFactsParseError(
            "agent_id cannot be empty or whitespace. "
            "Provide a meaningful identifier like 'data-analyst'."
        )

    # Parse optional fields with alias support
    # Priority: canonical name > alias name
    name = data.get("name")
    if name is None:
        name = data.get("agent_name")  # Alias

    description = data.get("description")
    if description is None:
        description = data.get("about_response")  # Alias from agent_configs

    expertise = data.get("expertise")
    if expertise is None:
        expertise = data.get("capabilities")  # Alias

    endpoint = data.get("endpoint")
    if endpoint is None:
        endpoint = data.get("agent_url")  # Alias

    # Validate expertise is a list if provided
    if expertise is not None and not isinstance(expertise, list):
        raise AgentFactsParseError(
            f"expertise must be a list, got {type(expertise).__name__}. "
            "Example: ['coding', 'testing']"
        )

    return AgentFacts(
        agent_id=agent_id.strip(),
        name=name,
        description=description,
        expertise=expertise,
        endpoint=endpoint,
        version=data.get("version")
    )


def validate_agent_facts(facts: AgentFacts) -> List[str]:
    """
    Validate AgentFacts completeness.

    Returns list of warnings for missing recommended fields.
    Empty list means the AgentFacts is complete.
    """
    warnings = []

    if not facts.name:
        warnings.append("Missing recommended field: name (display name for UI)")
    if not facts.description:
        warnings.append("Missing recommended field: description (helps users understand the agent)")
    if not facts.expertise:
        warnings.append("Missing recommended field: expertise (list of agent capabilities)")
    if not facts.endpoint:
        warnings.append("Missing recommended field: endpoint (URL to reach the agent)")

    return warnings


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def minimal_facts():
    """Minimal valid AgentFacts data (only required fields)."""
    return {"agent_id": "test-agent"}


@pytest.fixture
def complete_facts():
    """Complete AgentFacts data with all fields."""
    return {
        "agent_id": "data-scientist",
        "name": "Dr. Data",
        "description": "An analytical data science assistant",
        "expertise": ["data analysis", "machine learning", "Python"],
        "endpoint": "http://localhost:6001/a2a",
        "version": "1.0.0"
    }


@pytest.fixture
def facts_with_aliases():
    """AgentFacts using alias field names (from agent_configs.py format)."""
    return {
        "agent_id": "helpful-assistant",
        "agent_name": "Helper",
        "about_response": "I am a helpful assistant",
        "capabilities": ["general assistance", "information lookup"],
        "agent_url": "http://localhost:6000/a2a"
    }


# =============================================================================
# Tests
# =============================================================================

pytestmark = pytest.mark.unit


class TestParseRequiredFields:
    """Tests for required field validation."""

    def test_accepts_minimal_valid_input(self, minimal_facts):
        """
        Given: JSON with only agent_id
        When: Parsing
        Then: AgentFacts is created successfully
        """
        facts = parse_agent_facts(minimal_facts)

        assert facts.agent_id == "test-agent", (
            f"Expected 'test-agent', got '{facts.agent_id}'. "
            f"Cause: agent_id not extracted correctly. "
            f"Fix: Check parse_agent_facts() agent_id handling"
        )

    def test_rejects_missing_agent_id(self):
        """
        Given: JSON without agent_id field
        When: Parsing
        Then: AgentFactsParseError with helpful message
        """
        data = {"name": "Test Agent", "description": "A test"}

        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts(data)

        error_msg = str(exc.value).lower()
        assert "agent_id" in error_msg, (
            f"Error should mention 'agent_id'. Got: '{exc.value}'. "
            f"Cause: Missing field name in error. "
            f"Fix: Include field name in AgentFactsParseError"
        )

    def test_rejects_empty_agent_id(self):
        """
        Given: JSON with empty string agent_id
        When: Parsing
        Then: AgentFactsParseError explaining the issue
        """
        data = {"agent_id": ""}

        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts(data)

        error_msg = str(exc.value).lower()
        assert "empty" in error_msg or "agent_id" in error_msg, (
            f"Error should explain empty agent_id issue. Got: '{exc.value}'. "
            f"Cause: No empty string validation. "
            f"Fix: Add .strip() check in parse_agent_facts()"
        )

    def test_rejects_whitespace_only_agent_id(self):
        """
        Given: JSON with whitespace-only agent_id
        When: Parsing
        Then: AgentFactsParseError raised
        """
        data = {"agent_id": "   \t\n  "}

        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts(data)

        assert "agent_id" in str(exc.value).lower(), (
            f"Error should reference agent_id. Got: '{exc.value}'. "
            f"Cause: Whitespace not trimmed before validation. "
            f"Fix: Use .strip() before checking if empty"
        )

    def test_trims_whitespace_from_agent_id(self):
        """
        Given: JSON with agent_id surrounded by whitespace
        When: Parsing
        Then: Whitespace is trimmed from result
        """
        data = {"agent_id": "  my-agent  "}

        facts = parse_agent_facts(data)

        assert facts.agent_id == "my-agent", (
            f"Expected trimmed 'my-agent', got '{facts.agent_id}'. "
            f"Cause: Whitespace not trimmed. "
            f"Fix: Apply .strip() to agent_id"
        )


class TestParseOptionalFields:
    """Tests for optional field parsing."""

    def test_parses_name(self, minimal_facts):
        """
        Given: JSON with name field
        When: Parsing
        Then: Name is preserved
        """
        minimal_facts["name"] = "Test Agent Display"

        facts = parse_agent_facts(minimal_facts)

        assert facts.name == "Test Agent Display", (
            f"Expected 'Test Agent Display', got '{facts.name}'. "
            f"Cause: Name field not extracted. "
            f"Fix: Check data.get('name') in parser"
        )

    def test_parses_description(self, minimal_facts):
        """
        Given: JSON with description field
        When: Parsing
        Then: Description is preserved
        """
        minimal_facts["description"] = "A helpful test agent"

        facts = parse_agent_facts(minimal_facts)

        assert facts.description == "A helpful test agent", (
            f"Expected description text, got '{facts.description}'. "
            f"Cause: Description not extracted. "
            f"Fix: Check data.get('description') in parser"
        )

    def test_parses_expertise_list(self, minimal_facts):
        """
        Given: JSON with expertise array
        When: Parsing
        Then: List is preserved with all items
        """
        minimal_facts["expertise"] = ["coding", "testing", "debugging"]

        facts = parse_agent_facts(minimal_facts)

        assert facts.expertise == ["coding", "testing", "debugging"], (
            f"Expected 3-item list, got '{facts.expertise}'. "
            f"Cause: List not parsed correctly. "
            f"Fix: Ensure list is passed through unchanged"
        )

    def test_parses_endpoint_url(self, minimal_facts):
        """
        Given: JSON with endpoint URL
        When: Parsing
        Then: URL is preserved
        """
        minimal_facts["endpoint"] = "http://localhost:5000/a2a"

        facts = parse_agent_facts(minimal_facts)

        assert facts.endpoint == "http://localhost:5000/a2a", (
            f"Expected URL, got '{facts.endpoint}'. "
            f"Cause: Endpoint not extracted. "
            f"Fix: Check data.get('endpoint') in parser"
        )

    def test_parses_version(self, minimal_facts):
        """
        Given: JSON with version string
        When: Parsing
        Then: Version is preserved
        """
        minimal_facts["version"] = "2.1.0"

        facts = parse_agent_facts(minimal_facts)

        assert facts.version == "2.1.0", (
            f"Expected '2.1.0', got '{facts.version}'. "
            f"Cause: Version not extracted. "
            f"Fix: Check data.get('version') in parser"
        )


class TestParseFieldAliases:
    """Tests for field alias support (backward compatibility)."""

    def test_agent_name_maps_to_name(self, minimal_facts):
        """
        Given: JSON with agent_name (alias)
        When: Parsing
        Then: agent_name maps to name field
        """
        minimal_facts["agent_name"] = "Aliased Name"

        facts = parse_agent_facts(minimal_facts)

        assert facts.name == "Aliased Name", (
            f"Expected agent_name to map to name. Got: '{facts.name}'. "
            f"Cause: Alias not supported. "
            f"Fix: Add fallback: data.get('name') or data.get('agent_name')"
        )

    def test_canonical_name_takes_priority(self, minimal_facts):
        """
        Given: JSON with both name and agent_name
        When: Parsing
        Then: Canonical 'name' takes priority over alias
        """
        minimal_facts["name"] = "Canonical Name"
        minimal_facts["agent_name"] = "Alias Name"

        facts = parse_agent_facts(minimal_facts)

        assert facts.name == "Canonical Name", (
            f"Expected canonical name to win. Got: '{facts.name}'. "
            f"Cause: Alias overwriting canonical. "
            f"Fix: Check canonical field first, then alias"
        )

    def test_about_response_maps_to_description(self, minimal_facts):
        """
        Given: JSON with about_response (from agent_configs format)
        When: Parsing
        Then: about_response maps to description
        """
        minimal_facts["about_response"] = "I am a helpful agent"

        facts = parse_agent_facts(minimal_facts)

        assert facts.description == "I am a helpful agent", (
            f"Expected about_response to map to description. "
            f"Cause: Alias not supported. "
            f"Fix: Add fallback for about_response"
        )

    def test_capabilities_maps_to_expertise(self, minimal_facts):
        """
        Given: JSON with capabilities (alias for expertise)
        When: Parsing
        Then: capabilities maps to expertise
        """
        minimal_facts["capabilities"] = ["skill1", "skill2"]

        facts = parse_agent_facts(minimal_facts)

        assert facts.expertise == ["skill1", "skill2"], (
            f"Expected capabilities to map to expertise. "
            f"Cause: Alias not supported. "
            f"Fix: Add fallback for capabilities"
        )

    def test_agent_url_maps_to_endpoint(self, minimal_facts):
        """
        Given: JSON with agent_url (alias for endpoint)
        When: Parsing
        Then: agent_url maps to endpoint
        """
        minimal_facts["agent_url"] = "http://example.com/agent"

        facts = parse_agent_facts(minimal_facts)

        assert facts.endpoint == "http://example.com/agent", (
            f"Expected agent_url to map to endpoint. "
            f"Cause: Alias not supported. "
            f"Fix: Add fallback for agent_url"
        )

    def test_parses_full_aliased_config(self, facts_with_aliases):
        """
        Given: Full config using alias field names
        When: Parsing
        Then: All fields correctly mapped
        """
        facts = parse_agent_facts(facts_with_aliases)

        assert facts.agent_id == "helpful-assistant"
        assert facts.name == "Helper"
        assert facts.description == "I am a helpful assistant"
        assert "general assistance" in facts.expertise
        assert facts.endpoint == "http://localhost:6000/a2a"


class TestParseCompleteConfig:
    """Tests for complete configuration parsing."""

    def test_parses_complete_config(self, complete_facts):
        """
        Given: Complete AgentFacts with all fields
        When: Parsing
        Then: All fields correctly extracted
        """
        facts = parse_agent_facts(complete_facts)

        assert facts.agent_id == "data-scientist"
        assert facts.name == "Dr. Data"
        assert facts.description == "An analytical data science assistant"
        assert len(facts.expertise) == 3
        assert "machine learning" in facts.expertise
        assert facts.endpoint == "http://localhost:6001/a2a"
        assert facts.version == "1.0.0"

    def test_ignores_unknown_fields(self, minimal_facts):
        """
        Given: JSON with extra unrecognized fields
        When: Parsing
        Then: Parsing succeeds, extras ignored
        """
        minimal_facts["unknown_field"] = "some value"
        minimal_facts["another_extra"] = {"nested": "data"}

        facts = parse_agent_facts(minimal_facts)

        assert facts.agent_id == "test-agent", (
            f"Should parse successfully with unknown fields. "
            f"Cause: Unknown fields causing error. "
            f"Fix: Only extract known fields, ignore rest"
        )


class TestParseErrorHandling:
    """Tests for error handling with invalid input."""

    def test_rejects_none_input(self):
        """
        Given: None as input
        When: Parsing
        Then: AgentFactsParseError with clear message
        """
        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts(None)

        assert "none" in str(exc.value).lower(), (
            f"Error should mention None input. Got: '{exc.value}'. "
            f"Cause: No None check. "
            f"Fix: Add explicit None check at start"
        )

    def test_rejects_string_input(self):
        """
        Given: String instead of dict
        When: Parsing
        Then: AgentFactsParseError explaining expected type
        """
        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts('{"agent_id": "test"}')

        error_msg = str(exc.value).lower()
        assert "dict" in error_msg or "object" in error_msg, (
            f"Error should mention expected type. Got: '{exc.value}'. "
            f"Cause: No type hint in error. "
            f"Fix: Include 'expected dict' in error message"
        )

    def test_rejects_list_input(self):
        """
        Given: List instead of dict
        When: Parsing
        Then: AgentFactsParseError raised
        """
        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts([{"agent_id": "test"}])

        assert "dict" in str(exc.value).lower(), (
            f"Error should explain dict expected. Got: '{exc.value}'. "
            f"Cause: List not detected as wrong type. "
            f"Fix: Check isinstance(data, dict)"
        )

    def test_rejects_numeric_agent_id(self):
        """
        Given: agent_id as integer
        When: Parsing
        Then: AgentFactsParseError about string type
        """
        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts({"agent_id": 12345})

        error_msg = str(exc.value).lower()
        assert "string" in error_msg or "str" in error_msg, (
            f"Error should mention string requirement. Got: '{exc.value}'. "
            f"Cause: Type not validated. "
            f"Fix: Add isinstance(agent_id, str) check"
        )

    def test_rejects_non_list_expertise(self):
        """
        Given: expertise as string instead of list
        When: Parsing
        Then: AgentFactsParseError about list type
        """
        data = {"agent_id": "test", "expertise": "coding, testing"}

        with pytest.raises(AgentFactsParseError) as exc:
            parse_agent_facts(data)

        error_msg = str(exc.value).lower()
        assert "list" in error_msg, (
            f"Error should mention list requirement. Got: '{exc.value}'. "
            f"Cause: String expertise not rejected. "
            f"Fix: Add isinstance(expertise, list) check"
        )


class TestParseEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_preserves_unicode_in_name(self):
        """
        Given: Name with unicode characters
        When: Parsing
        Then: Unicode preserved correctly
        """
        data = {"agent_id": "test", "name": "\u4e2d\u6587\u4ee3\u7406"}  # Chinese

        facts = parse_agent_facts(data)

        assert facts.name == "\u4e2d\u6587\u4ee3\u7406", (
            f"Unicode not preserved. Got: '{facts.name}'. "
            f"Cause: Encoding issue. "
            f"Fix: Ensure UTF-8 handling throughout"
        )

    def test_preserves_special_chars_in_agent_id(self):
        """
        Given: agent_id with hyphens, underscores, numbers
        When: Parsing
        Then: All characters preserved
        """
        data = {"agent_id": "my-test_agent-v1.0"}

        facts = parse_agent_facts(data)

        assert facts.agent_id == "my-test_agent-v1.0", (
            f"Special chars not preserved. Got: '{facts.agent_id}'. "
            f"Cause: Character filtering. "
            f"Fix: Don't sanitize agent_id"
        )

    def test_handles_empty_expertise_list(self):
        """
        Given: Empty expertise list []
        When: Parsing
        Then: Empty list preserved (not converted to None)
        """
        data = {"agent_id": "test", "expertise": []}

        facts = parse_agent_facts(data)

        assert facts.expertise == [], (
            f"Empty list should stay as []. Got: {facts.expertise}. "
            f"Cause: Falsy check converting [] to None. "
            f"Fix: Use 'is None' not 'if not expertise'"
        )

    def test_handles_json_null_values(self):
        """
        Given: JSON with explicit null values
        When: Parsing
        Then: Nulls treated as missing (None in Python)
        """
        data = {"agent_id": "test", "name": None, "description": None}

        facts = parse_agent_facts(data)

        assert facts.name is None, "Null should become None"
        assert facts.description is None, "Null should become None"

    def test_handles_long_description(self):
        """
        Given: Very long description (10KB)
        When: Parsing
        Then: Full content preserved without truncation
        """
        long_text = "A" * 10240
        data = {"agent_id": "test", "description": long_text}

        facts = parse_agent_facts(data)

        assert len(facts.description) == 10240, (
            f"Expected 10240 chars, got {len(facts.description)}. "
            f"Cause: Text truncation. "
            f"Fix: Remove any length limits"
        )

    def test_handles_deeply_nested_unknown_fields(self):
        """
        Given: JSON with nested unknown structures
        When: Parsing
        Then: Parsing succeeds, nested data ignored
        """
        data = {
            "agent_id": "test",
            "metadata": {
                "created": "2024-01-01",
                "nested": {"deep": {"value": 123}}
            }
        }

        facts = parse_agent_facts(data)

        assert facts.agent_id == "test", (
            "Should succeed with nested unknown fields"
        )


class TestValidateAgentFacts:
    """Tests for validation warnings."""

    def test_warns_on_minimal_facts(self, minimal_facts):
        """
        Given: AgentFacts with only required field
        When: Validating
        Then: Warnings for all missing recommended fields
        """
        facts = parse_agent_facts(minimal_facts)

        warnings = validate_agent_facts(facts)

        assert len(warnings) == 4, (
            f"Expected 4 warnings (name, description, expertise, endpoint). "
            f"Got {len(warnings)}: {warnings}"
        )

    def test_no_warnings_for_complete_facts(self, complete_facts):
        """
        Given: Complete AgentFacts with all fields
        When: Validating
        Then: No warnings
        """
        facts = parse_agent_facts(complete_facts)

        warnings = validate_agent_facts(facts)

        assert len(warnings) == 0, (
            f"Expected no warnings for complete facts. Got: {warnings}"
        )

    def test_warning_messages_are_helpful(self, minimal_facts):
        """
        Given: AgentFacts missing fields
        When: Validating
        Then: Warning messages explain what's missing and why
        """
        facts = parse_agent_facts(minimal_facts)

        warnings = validate_agent_facts(facts)

        # Each warning should mention the field name
        warning_text = " ".join(warnings).lower()
        assert "name" in warning_text, "Should mention missing name"
        assert "description" in warning_text, "Should mention missing description"
