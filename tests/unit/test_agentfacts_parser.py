"""
Placeholder Tests for AgentFacts.

Status: FEATURE NOT DEFINED
----------------------------
"AgentFacts" is mentioned in PLAN_TEST.md but:
- No AgentFacts class exists in nanda_core
- No specification defines what AgentFacts should contain
- The A2A protocol uses "AgentCard" (from python_a2a) not "AgentFacts"

The python_a2a library provides AgentCard with these fields:
- name: str
- description: str
- url: str
- version: str
- authentication: Optional[str]
- capabilities: Dict[str, Any]
- default_input_modes: List[str]
- default_output_modes: List[str]
- skills: List[AgentSkill]
- provider: Optional[str]
- documentation_url: Optional[str]

If "AgentFacts" is intended to be different from AgentCard, a specification
is needed before tests can be written. These placeholder tests document
that the feature is undefined.

See: python_a2a.AgentCard for existing agent metadata support.
"""

import pytest

pytestmark = pytest.mark.unit


def _not_implemented(message: str):
    """Raise NotImplementedError - feature not defined."""
    raise NotImplementedError(
        f"AgentFacts: {message}. "
        f"No specification exists. "
        f"Consider using python_a2a.AgentCard instead."
    )


class TestAgentFactsPlaceholder:
    """
    Placeholder tests for undefined AgentFacts feature.

    These tests exist to:
    1. Document that AgentFacts is not implemented
    2. Track that tests should be added when spec is defined
    3. Distinguish from AgentCard (which exists in python_a2a)
    """

    def test_agentfacts_needs_specification(self):
        """
        AgentFacts parser requires a specification before implementation.

        Questions that need answers:
        - What is the difference between AgentFacts and AgentCard?
        - What fields are required vs optional?
        - What is the input format (JSON, dict, URL)?
        - What is the output format (dataclass, Pydantic model)?
        - Where should it be implemented in nanda_core?
        """
        _not_implemented("specification needed")

    def test_agentfacts_vs_agentcard_distinction(self):
        """
        Need to clarify relationship between AgentFacts and AgentCard.

        python_a2a already provides AgentCard with:
        - name, description, url, version
        - authentication, capabilities
        - skills, provider, documentation_url

        Is AgentFacts a subset? Superset? Different purpose?
        """
        _not_implemented("relationship to AgentCard unclear")

    def test_agentfacts_use_case(self):
        """
        Need to define the use case for AgentFacts.

        Possible purposes:
        - Simplified agent metadata (vs full AgentCard)?
        - Internal nanda_core representation?
        - Different serialization format?
        """
        _not_implemented("use case not defined")

    def test_agentfacts_location_in_codebase(self):
        """
        Need to determine where AgentFacts should live.

        Options:
        - nanda_core/core/agentfacts.py (new module)?
        - Extension of existing agent_bridge.py?
        - Wrapper around python_a2a.AgentCard?
        """
        _not_implemented("implementation location not determined")

    def test_agentfacts_parsing_requirements(self):
        """
        If AgentFacts needs parsing, requirements must be defined.

        Questions:
        - Parse from what format? (JSON, YAML, .well-known URL?)
        - Validation rules?
        - Error handling approach?
        """
        _not_implemented("parsing requirements not specified")
