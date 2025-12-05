# NEST Test Plan - Issue #7

## Overview

Four-layer test strategy following Issue #7 specification.

---

## Current Status

| Layer | Status | Tests | Files |
|-------|--------|-------|-------|
| **Unit** | **COMPLETE** | 146 | 5 files |
| Integration | Not Started | 0 | 0 files |
| E2E | Not Started | 0 | 0 files |
| Contract | Not Started | 0 | 0 files |
| Performance | Not Started | 0 | 0 files |

**Total: 146 tests passing**

---

## Layer 1: Unit Tests (COMPLETE)

### Files and Test Counts

| File | Tests | Coverage |
|------|-------|----------|
| `test_protocol_adapters.py` | 14 | A2A format, metadata, edge cases |
| `test_protocol_router.py` | 22 | 5 routing patterns, priority, errors |
| `test_agentfacts_parser.py` | 32 | Parse, validate, aliases, edge cases |
| `test_mention_extraction_and_routing.py` | 47 | Standard/unicode formats, boundaries, position, commands |
| `test_framework_adapters.py` | 31 | Required/optional params, formats, edge cases |

### Detailed Breakdown

#### Protocol Adapters (14 tests)
- TestA2AMessageFormatting (4) - role, content type, agent ID prefix, non-text rejection
- TestA2AMessageMetadata (4) - conversation ID, parent ID, unique message IDs
- TestA2AErrorHandling (1) - exception handling
- TestA2AEdgeCases (5) - empty, special chars, unicode, long text, whitespace

#### Protocol Router (22 tests)
- TestRegularMessageRouting (4) - agent_logic routing, telemetry
- TestAtPrefixRouting (4) - @agent-id outgoing A2A
- TestHashPrefixRouting (2) - #registry:server MCP
- TestSlashPrefixRouting (3) - /command system commands
- TestIncomingA2ARouting (3) - FROM:/TO:/MESSAGE: format
- TestRoutingPriority (3) - priority order verification
- TestRoutingErrorHandling (3) - exceptions, non-text, conversation preservation

#### AgentFacts Parser (32 tests)
- TestParseRequiredFields (5) - agent_id validation
- TestParseOptionalFields (5) - name, description, expertise, endpoint, version
- TestParseFieldAliases (6) - agent_name, about_response, capabilities aliases
- TestParseCompleteConfig (2) - full config, unknown fields
- TestParseErrorHandling (5) - None, string, list, numeric, non-list expertise
- TestParseEdgeCases (6) - unicode, special chars, empty list, null, long text
- TestValidateAgentFacts (3) - warnings for incomplete facts

#### @mention Extraction & Routing (47 tests)
- TestMentionStandardFormats (11) - simple, hyphens, underscores, numbers, dots, case, single char
- TestMentionUnicodeFormats (5) - Chinese, Japanese, Cyrillic, French, Greek
- TestMentionBoundaryConditions (5) - no body, whitespace only, @ alone, @ space, empty
- TestMentionPositionEdgeCases (3) - at start, not at start, email in message
- TestMentionMessageContent (7) - special chars, unicode, newlines, tabs, long ID, long body, minimal
- TestMentionErrorHandling (1) - non-text content
- TestCommandHelp (2) - header, lists all commands
- TestCommandPing (2) - returns pong, ignores extra args
- TestCommandStatus (4) - agent ID, running state, registry URL, omits when unconfigured
- TestCommandUnknown (2) - unknown error, uppercase handling
- TestCommandEdgeCases (5) - / only, / spaces, leading whitespace, //, newline in args

#### Framework Adapters (31 tests)
- TestImportVerification (1) - SimpleAgentBridge importable
- TestRequiredParameters (2) - init with required params, callable agent_logic
- TestOptionalParameterDefaults (4) - registry_url, mcp_registry_url, smithery_api_key, telemetry
- TestOptionalParameterValues (4) - custom values stored correctly
- TestFullConfiguration (2) - all params, functional bridge
- TestAgentIdFormats (7) - simple, hyphens, underscores, numbers, uppercase, mixed, dots
- TestUrlFormats (5) - localhost, port, https, path, port+path
- TestEdgeCases (6) - empty agent_id, long ID, empty URL, whitespace, unicode, special chars

---

## Layer 2: Integration Tests (NOT STARTED)

### Required Files

| File | Purpose |
|------|---------|
| `test_protocol_flows.py` | Protocol communication flows with mock external agents |
| `test_registry_client.py` | Registry client interactions with mock NANDA Index |
| `test_payment_flow.py` | Payment flow with mock blockchain facilitator |
| `test_framework_bridge.py` | Framework-to-protocol bridge |

### Key Test Areas
- A2A message sending/receiving with mocked agents
- Registry registration, lookup, update flows
- x402 payment header handling
- Framework message to A2A conversion

---

## Layer 3: E2E Tests (NOT STARTED)

### Required Files

| File | Purpose |
|------|---------|
| `test_multi_agent_scenarios.py` | Multi-agent scenarios with real protocol communication |
| `test_agent_discovery.py` | Agent discovery via local registry |
| `test_cross_framework.py` | Cross-framework agent collaboration |

### Requirements
- Docker Compose setup
- Real A2A protocol communication
- Multiple agent instances

---

## Layer 4: Contract Tests (NOT STARTED)

### Required Files

| File | Purpose |
|------|---------|
| `test_a2a_compliance.py` | A2A spec compliance (AgentCard, JSON-RPC 2.0) |
| `test_slim_compliance.py` | SLIM protocol compliance |
| `test_x402_payments.py` | x402 payment headers |

### Key Test Areas
- AgentCard format validation
- JSON-RPC 2.0 message format
- SLIM message structure
- x402 header format

---

## Test Quality Standards

All tests follow these requirements:

### 1. Best Practice
- Test actual function behavior
- Meaningful assertions with error messages
- Use fixtures for reusable test data
- Use `pytestmark` for module-level markers

### 2. Well Documented
- Given-When-Then docstring format
- Module docstring explaining scope
- Class docstrings describing purpose

### 3. Developer Friendly
- Descriptive test names: `test_[action]_[expected]`
- Error messages: Expected/Got/Cause/Fix format
```python
assert result == expected, (
    f"Expected '{expected}', got '{result}'. "
    f"Cause: X changed. "
    f"Fix: Check Y()"
)
```

### 4. No Redundancy
- Parameterized tests where applicable
- Fixtures instead of repeated setup
- One behavior per test

### 5. Highly Structured
- One class per feature area
- Section comments separating categories
- Consistent naming conventions

---

## Quick Commands

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_protocol_router.py -v

# Run with coverage
pytest tests/unit/ --cov=nanda_core --cov-report=html

# Run fast (no coverage)
pytest tests/unit/ --no-cov
```

---

## Remaining Work

### Priority 1: Integration Tests
1. Create `tests/integration/` directory structure
2. Implement `test_protocol_flows.py` - mock A2A communication
3. Implement `test_registry_client.py` - mock registry interactions
4. Implement `test_payment_flow.py` - mock payment handling
5. Implement `test_framework_bridge.py` - framework conversion

### Priority 2: Contract Tests
1. Create `tests/contract/` directory structure
2. Implement A2A spec compliance tests
3. Implement SLIM protocol compliance tests
4. Implement x402 header validation tests

### Priority 3: E2E Tests
1. Create `tests/e2e/` directory structure
2. Set up Docker Compose for test environment
3. Implement multi-agent scenario tests
4. Implement agent discovery tests
5. Implement cross-framework tests

### Priority 4: Performance Tests
1. Create `tests/performance/` directory structure
2. Implement large-scale agent tests
3. Implement message throughput tests
