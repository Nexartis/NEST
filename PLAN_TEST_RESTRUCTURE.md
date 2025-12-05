# Test Restructuring Plan V2: Exact Issue #7 Structure

## Issue #7's Exact Test Organization

### 1. Unit Tests (Component-level, isolated)
- `test_protocol_adapters.py` - A2A, SLIM message formatting
- `test_protocol_router.py` - Protocol router logic
- `test_agentfacts_parser.py` - AgentFacts parsing
- `test_mention_routing.py` - @mention extraction and routing
- `test_framework_adapters.py` - Framework/LLM provider adapters

### 2. Integration Tests (Component interaction with mocks)
- `test_protocol_flows.py` - Protocol communication flows (mock external agents)
- `test_registry_client.py` - Registry client interactions (mock NANDA Index)
- `test_payment_flow.py` - Payment flow (mock blockchain facilitator)
- `test_framework_bridge.py` - Framework-to-protocol bridge

### 3. E2E Tests (Full system, real protocols)
- `test_multi_agent_scenarios.py` - Multi-agent scenarios with real protocol communication
- `test_agent_discovery.py` - Agent discovery via local registry
- `test_cross_framework.py` - Cross-framework agent collaboration

### 4. Contract Tests (Protocol compliance)
- `test_a2a_compliance.py` - A2A spec compliance (AgentCard format, JSON-RPC 2.0)
- `test_slim_compliance.py` - SLIM protocol compliance
- `test_x402_payments.py` - x402 payment headers

---

## Mapping Existing Tests (PR #20 + PR #24) to Issue #7 Structure

### From PR #24 (test_agent_bridge.py - 20 tests):

**Can map to Unit Tests:**
- `TestSimpleAgentBridgeInit` (3 tests) → `test_framework_bridge.py` (unit tests for bridge initialization)
- `TestMessageRouting` (4 tests) → `test_protocol_router.py` (routing logic)
- `TestSystemCommands` (3 tests) → `test_mention_routing.py` (@mention commands)
- `TestResponseFormat` (2 tests) → `test_protocol_adapters.py` (message formatting)

**Can map to Integration Tests:**
- `TestAgentToAgentMessages` (4 tests) → `test_protocol_flows.py` (A2A communication flows)
- `TestMCPMessages` (2 tests) → `test_protocol_flows.py` (MCP protocol flows)
- `TestIncomingAgentMessages` (2 tests) → `test_protocol_flows.py` (incoming message handling)

### From PR #20 (test_generic_agent_patterns.py - 14 tests):

**Can map to Unit Tests:**
- `TestAgentRegistration` (3 tests) → Doesn't fit Issue #7 unit structure (was generic testing, not NEST-specific)
- `TestAgentDelegation` (3 tests) → Doesn't fit Issue #7 unit structure
- `TestAgentMessaging` (3 tests) → Could contribute to `test_protocol_adapters.py` patterns

**Can map to Integration Tests:**
- `TestAgentTestHarness` (3 tests) → Move to `conftest.py` as test utilities (not actual tests)
- `TestEndToEndWorkflow` (2 tests) → Could inform `test_protocol_flows.py` or `test_registry_client.py`

**Performance Tests:**
- `TestLargeScaleScenarios` (2 tests) → Keep in `tests/performance/test_large_scale.py`

### Tests that don't map to Issue #7:

**PR #20's generic fixtures and patterns:**
- These are **test infrastructure**, not NEST-specific tests
- Should be kept in `conftest.py` as reusable fixtures
- The test harness (MockRegistry, MockAdapter, AgentTestHarness) are tools, not tests themselves

**Decision:** Keep PR #20's infrastructure in conftest.py, but PR #20's actual tests need to be reconsidered - they test the test infrastructure itself, not NEST components.

---

## Proposed New Structure (Exact Issue #7 Match)

```
tests/
├── conftest.py                 # All fixtures (PR #20 + PR #24)
├── pytest.ini                  # Configuration
├── README.md                   # Test documentation
│
├── unit/                       # Layer 1: NEST Component Unit Tests
│   ├── __init__.py
│   ├── test_protocol_adapters.py      # A2A, SLIM message formatting
│   │   # - FROM PR #24: TestResponseFormat (2 tests)
│   │   # - TODO: A2A adapter tests
│   │   # - TODO: SLIM adapter tests
│   │
│   ├── test_protocol_router.py        # Protocol router logic
│   │   # - FROM PR #24: TestMessageRouting (4 tests)
│   │   # - TODO: Router decision logic
│   │   # - TODO: Message dispatch tests
│   │
│   ├── test_mention_extraction_and_routing.py   # @mention extraction and routing
│   │   # - FROM PR #24: TestSystemCommands (3 tests for @mention commands)
│   │   # - TODO: @mention parser tests
│   │   # - TODO: Routing table tests
│   │
│   ├── test_agentfacts_parser.py      # AgentFacts parsing
│   │   # - TODO: AgentCard parsing
│   │   # - TODO: AgentFacts validation
│   │
│   └── test_framework_adapters.py     # Framework/LLM provider adapters
│       # - FROM PR #24: TestSimpleAgentBridgeInit (3 tests)
│       # - TODO: Claude Desktop adapter
│       # - TODO: Other framework adapters
│
├── integration/                # Layer 2: NEST Component Integration Tests
│   ├── __init__.py
│   ├── test_protocol_communication_flows.py    # Protocol communication flows (mock external agents)
│   │   # - FROM PR #24: TestAgentToAgentMessages (4 tests)
│   │   # - FROM PR #24: TestMCPMessages (2 tests)
│   │   # - FROM PR #24: TestIncomingAgentMessages (2 tests)
│   │   # - TODO: Mock external agent responses
│   │
│   ├── test_registry_client_interactions.py    # Registry client interactions (mock NANDA Index)
│   │   # - USE PR #20 MockRegistry fixture
│   │   # - TODO: Registration flow tests
│   │   # - TODO: Lookup flow tests
│   │   # - TODO: Update flow tests
│   │
│   ├── test_payment_flow.py           # Payment flow (mock blockchain facilitator)
│   │   # - TODO: x402 payment header handling
│   │   # - TODO: Mock blockchain facilitator
│   │
│   └── test_framework_to_protocol_bridge.py    # Framework-to-protocol bridge
│       # - TODO: Framework message → A2A conversion
│       # - TODO: A2A response → Framework message
│
├── e2e/                        # Layer 3: NEST End-to-End Tests
│   ├── __init__.py
│   ├── docker-compose.test.yml        # Docker setup for E2E
│   ├── test_multi_agent_scenarios.py  # Multi-agent scenarios with real protocol communication
│   │   # - TODO: 2-3 agents communicating via real A2A
│   │
│   ├── test_agent_discovery_via_local_registry.py  # Agent discovery via local registry
│   │   # - TODO: Agent publishes to registry
│   │   # - TODO: Agent discovers other agents
│   │
│   └── test_cross_framework_agent_collaboration.py  # Cross-framework agent collaboration
│       # - TODO: Claude Desktop agent ↔ Different framework agent
│
├── contract/                   # Layer 4: Protocol Compliance Tests
│   ├── __init__.py
│   ├── test_a2a_spec_compliance.py    # A2A spec compliance (AgentCard format, JSON-RPC 2.0)
│   │   # - TODO: AgentCard format validation
│   │   # - TODO: JSON-RPC 2.0 compliance
│   │
│   ├── test_slim_compliance.py        # SLIM protocol compliance
│   │   # - TODO: SLIM message format validation
│   │
│   └── test_x402_payment_headers.py   # x402 payment headers
│       # - TODO: x402 header format validation
│
└── performance/                # Performance tests (from PR #20)
    ├── __init__.py
    └── test_large_scale.py            # Large scale scenarios
        # - FROM PR #20: TestLargeScaleScenarios (2 tests)
        # - 100 agents, 1000 messages tests
```

---

## What Happens to PR #20's Generic Tests?

**PR #20's test files tested the test infrastructure itself:**
- `TestAgentRegistration` → Tests MockRegistry.register_agent()
- `TestAgentDelegation` → Tests MockRegistry.grant_delegation()
- `TestAgentMessaging` → Tests MockAdapter.send_message()
- `TestAgentTestHarness` → Tests AgentTestHarness helper class

**These are not NEST component tests** - they're tests for the testing tools.

**Options:**

**Option A: Keep as infrastructure validation tests**
```
tests/
└── infrastructure/
    └── test_fixtures.py    # PR #20 tests validating MockRegistry, MockAdapter work
```

**Option B: Remove them (RECOMMENDED)**
- The fixtures themselves (MockRegistry, MockAdapter) are kept in conftest.py
- We trust they work when we use them in actual NEST component tests
- Testing the test infrastructure is less important than testing NEST itself

**Option C: Incorporate patterns into actual NEST tests**
- Use PR #20's test patterns as examples when writing `test_registry_client.py`
- The patterns are good, just apply them to real NEST registry client

**Recommendation: Option C**
- Keep PR #20's fixtures in conftest.py (MockRegistry, MockAdapter, AgentTestHarness)
- Use PR #20's test patterns when implementing `test_registry_client.py`
- Don't keep tests that only validate the mocks themselves

---

## Revised Implementation Plan

### Phase 1: Create Issue #7 Exact Structure

```bash
# Create directories matching Issue #7 exactly
mkdir -p tests/{unit,integration,e2e,contract,performance}
touch tests/{unit,integration,e2e,contract,performance}/__init__.py
```

### Phase 2: Migrate PR #24 Tests to Issue #7 Structure

**2.1: Unit tests (extract from test_agent_bridge.py)**

`tests/unit/test_protocol_adapters.py`:
```python
"""Unit tests for A2A and SLIM protocol adapters."""
import pytest

# FROM PR #24: TestResponseFormat (2 tests)
@pytest.mark.unit
class TestMessageFormatting:
    def test_format_text_content(self, mock_agent_logic):
        # ... migrate from PR #24

    def test_format_agent_response(self, mock_agent_logic):
        # ... migrate from PR #24

# TODO: Add A2A/SLIM specific tests
@pytest.mark.unit
class TestA2AAdapter:
    def test_format_a2a_message(self):
        pytest.skip("TODO: Issue #7 - A2A message formatting")
```

`tests/unit/test_protocol_router.py`:
```python
"""Unit tests for protocol router logic."""
import pytest

# FROM PR #24: TestMessageRouting (4 tests)
@pytest.mark.unit
class TestMessageRouting:
    def test_route_user_message(self, bridge_instance, sample_text_message):
        # ... migrate from PR #24

    def test_route_system_command(self, bridge_instance):
        # ... migrate from PR #24
```

`tests/unit/test_mention_routing.py`:
```python
"""Unit tests for @mention extraction and routing."""
import pytest

# FROM PR #24: TestSystemCommands (3 tests)
@pytest.mark.unit
class TestMentionExtraction:
    def test_extract_mentions(self):
        # ... migrate from PR #24

# TODO: Add @mention routing logic tests
```

`tests/unit/test_framework_adapters.py`:
```python
"""Unit tests for framework/LLM provider adapters."""
import pytest

# FROM PR #24: TestSimpleAgentBridgeInit (3 tests)
@pytest.mark.unit
class TestSimpleAgentBridge:
    def test_init_with_agent_logic(self, mock_agent_logic):
        # ... migrate from PR #24
```

`tests/unit/test_agentfacts_parser.py`:
```python
"""Unit tests for AgentFacts parsing."""
import pytest

@pytest.mark.unit
class TestAgentFactsParser:
    def test_parse_agentcard(self):
        pytest.skip("TODO: Issue #7 - AgentCard parsing")
```

**2.2: Integration tests (extract from test_agent_bridge.py)**

`tests/integration/test_protocol_flows.py`:
```python
"""Integration tests for protocol communication flows."""
import pytest

# FROM PR #24: TestAgentToAgentMessages (4 tests)
@pytest.mark.integration
class TestA2ACommunication:
    def test_send_message_to_agent(self, bridge_instance):
        # ... migrate from PR #24

# FROM PR #24: TestMCPMessages (2 tests)
@pytest.mark.integration
class TestMCPProtocol:
    def test_handle_mcp_message(self, bridge_instance):
        # ... migrate from PR #24

# FROM PR #24: TestIncomingAgentMessages (2 tests)
@pytest.mark.integration
class TestIncomingMessages:
    def test_receive_agent_message(self, bridge_instance):
        # ... migrate from PR #24
```

`tests/integration/test_registry_client.py`:
```python
"""Integration tests for registry client with mock NANDA Index."""
import pytest

# USE PR #20's MockRegistry fixture patterns
@pytest.mark.integration
class TestRegistryClientIntegration:
    def test_register_agent_with_registry(self, mock_registry):
        """Test agent registration flow with mock NANDA Index."""
        # Use PR #20's MockRegistry, but test actual RegistryClient
        # TODO: Implement with real registry client
        pytest.skip("TODO: Issue #7 - Registry client integration")
```

`tests/integration/test_payment_flow.py`:
```python
"""Integration tests for payment flow."""
import pytest

@pytest.mark.integration
class TestPaymentFlow:
    def test_x402_payment_handling(self):
        pytest.skip("TODO: Issue #7 - Payment flow")
```

`tests/integration/test_framework_bridge.py`:
```python
"""Integration tests for framework-to-protocol bridge."""
import pytest

@pytest.mark.integration
class TestFrameworkBridge:
    def test_framework_message_to_a2a(self):
        pytest.skip("TODO: Issue #7 - Framework bridge")
```

**2.3: E2E tests (placeholders)**

`tests/e2e/test_multi_agent_scenarios.py`:
```python
"""E2E tests for multi-agent scenarios."""
import pytest

@pytest.mark.e2e
class TestMultiAgentScenarios:
    def test_two_agents_communicate(self):
        pytest.skip("TODO: Issue #7 - Requires Docker Compose")
```

**2.4: Contract tests (placeholders)**

`tests/contract/test_a2a_compliance.py`:
```python
"""Contract tests for A2A protocol compliance."""
import pytest

@pytest.mark.contract
class TestA2ACompliance:
    def test_agentcard_format_compliance(self):
        pytest.skip("TODO: Issue #7 - A2A spec compliance")
```

**2.5: Performance tests (migrate from PR #20)**

`tests/performance/test_large_scale.py`:
```python
"""Performance tests for large-scale scenarios."""
import pytest

# FROM PR #20: TestLargeScaleScenarios (2 tests)
@pytest.mark.slow
class TestLargeScaleScenarios:
    def test_many_agents_registration(self, agent_test_harness):
        # ... migrate from PR #20

    def test_many_messages(self, agent_test_harness):
        # ... migrate from PR #20
```

### Phase 3: Update Configuration

**pytest.ini:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers --cov=nanda_core --cov-report=html --cov-report=term-missing
markers =
    unit: Unit tests - fast, isolated component tests
    integration: Integration tests - component interaction with mocked external services
    e2e: End-to-end tests - full system tests requiring Docker Compose
    contract: Contract tests - protocol specification compliance verification
    slow: Slow running tests - performance and large-scale scenarios
```

**tests/README.md:**
```markdown
# NEST Testing Guide

## Test Organization (Issue #7 Four-Layer Strategy)

### 1. Unit Tests (`tests/unit/`)
Fast, isolated tests for individual NEST components:
- Protocol adapters (A2A, SLIM)
- Protocol router logic
- AgentFacts parsing
- @mention extraction and routing
- Framework/LLM provider adapters

**Run:** `pytest tests/unit/ -v`

### 2. Integration Tests (`tests/integration/`)
Component interaction tests with mocked external services:
- Protocol communication flows
- Registry client with mock NANDA Index
- Payment flow with mock blockchain
- Framework-to-protocol bridge

**Run:** `pytest tests/integration/ -v`

### 3. E2E Tests (`tests/e2e/`)
Full system tests with real protocol communication:
- Multi-agent scenarios
- Agent discovery via local registry
- Cross-framework collaboration

**Requires:** Docker Compose
**Run:** `docker-compose -f tests/e2e/docker-compose.test.yml up && pytest tests/e2e/ -v`

### 4. Contract Tests (`tests/contract/`)
Protocol specification compliance:
- A2A spec (AgentCard, JSON-RPC 2.0)
- SLIM protocol
- x402 payment headers

**Run:** `pytest tests/contract/ -v`

### Performance Tests (`tests/performance/`)
Large-scale and performance testing:
**Run:** `pytest tests/performance/ -m slow -v`

## Quick Commands

```bash
# All tests
pytest

# Fast tests only (unit)
pytest tests/unit/

# Skip slow tests
pytest -m "not slow"

# Coverage report
pytest --cov=nanda_core --cov-report=html
open htmlcov/index.html

# Specific test layer
pytest tests/unit/ tests/integration/  # Skip E2E
```
```

### Phase 4: Remove Old Files

```bash
git rm tests/test_agent_bridge.py
git rm tests/test_generic_agent_patterns.py
```

---

## Final Test Count

**After restructuring:**

| Layer | From PR #24 | From PR #20 | New TODOs | Total |
|-------|-------------|-------------|-----------|-------|
| Unit | 12 tests | 0 | ~10 tests | 22 tests |
| Integration | 8 tests | 0 | ~8 tests | 16 tests |
| E2E | 0 | 0 | ~6 tests | 6 tests |
| Contract | 0 | 0 | ~6 tests | 6 tests |
| Performance | 0 | 2 tests | ~2 tests | 4 tests |
| **Total** | **20** | **2** | **~32** | **54 tests** |

**Current state:** 22 working tests (20 from PR #24, 2 from PR #20)
**With placeholders:** 54 tests (22 passing, 32 skipped TODOs)

---

## Summary of Changes from V1

**V1 Problem:** Organized by PR origin, not by Issue #7 structure

**V2 Solution:** Exact Issue #7 file structure
- ✅ Unit tests: 5 files matching Issue #7 spec exactly
- ✅ Integration tests: 4 files matching Issue #7 spec exactly
- ✅ E2E tests: 3 files matching Issue #7 spec exactly
- ✅ Contract tests: 3 files matching Issue #7 spec exactly

**PR #20 Decision:**
- Keep fixtures (MockRegistry, MockAdapter, AgentTestHarness) in conftest.py
- Keep 2 performance tests in tests/performance/
- Remove generic pattern tests (they tested the mocks, not NEST)

**PR #24 Decision:**
- Distribute all 20 tests into appropriate Issue #7 categories
- No tests lost, just reorganized by purpose not by PR
