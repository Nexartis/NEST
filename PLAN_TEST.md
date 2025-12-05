# NEST Test Plan - Issue #7

## Overview

Four-layer test strategy following Issue #7 specification.

---

## Current Status

| Layer | Status | Tests | Files |
|-------|--------|-------|-------|
| **Unit** | **COMPLETE** | 175 | 5 files |
| **Integration** | **COMPLETE** | 232 | 4 files |
| E2E | Not Started | 0 | 0 files |
| Contract | Not Started | 0 | 0 files |
| Performance | Not Started | 0 | 0 files |

**Total: 407 tests passing** (175 unit + 232 integration)

---

## Layer 1: Unit Tests (COMPLETE)

### Files and Test Counts

| File | Tests | Coverage |
|------|-------|----------|
| `test_protocol_adapters.py` | 14 | A2A format, metadata, edge cases |
| `test_protocol_router.py` | 22 | 5 routing patterns, priority, errors |
| `test_agentfacts_parser.py` | 32 | Parse, validate, aliases, edge cases |
| `test_mention_extraction_and_routing.py` | 54 | Standard/unicode formats (12 languages), boundaries, position, commands |
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

## Layer 2: Integration Tests (COMPLETE)

### Files and Test Counts

| File | Tests | Coverage |
|------|-------|----------|
| `test_protocol_communication_flows.py` | 31 | A2A routing, registry lookup, message sending |
| `test_registry_client.py` | 82 | Registration, lookup, search, health, HTTP errors, Unicode (14 languages) |
| `test_mcp_integration.py` | 37 | NANDA/Smithery lookups, URL building, MCP client |
| `test_framework_adapter_bridge.py` | 71 | NANDA adapter, bridge creation, lifecycle, HTTP errors, Unicode (12 languages) |

### Detailed Breakdown

#### Protocol Communication Flows (31 tests)
- TestA2AMessageFormatValidation (7) - bare mention, valid format, middle mention, special chars
- TestRegistryLookupBehavior (8) - endpoint calls, 404, 500, timeout, connection error, invalid JSON
- TestA2AMessageSending (4) - client creation, response handling, send failure, empty response
- TestIncomingA2AMessageHandling (4) - FROM/TO/MESSAGE parsing, loop prevention, malformed
- TestMessageMetadataPreservation (2) - conversation ID preservation and generation
- TestA2AEdgeCasesAndBoundaries (6) - long message, unicode, self-mention, multiple @, whitespace, newlines

#### Registry Client (82 tests)
- TestRegistryClientInitialization (4) - URL config, defaults, file reading, SSL
- TestAgentRegistration (6) - POST endpoint, required/optional fields, success/failure, network error
- TestAgentLookup (4) - GET endpoint, success, 404, network error
- TestAgentListing (5) - list agents, list clients, fallback behavior
- TestAgentSearch (4) - query, capabilities, tags filters, local fallback
- TestMCPServerOperations (4) - mcp_servers endpoint, provider filter, config parsing
- TestAgentStatusOperations (6) - PUT status, timestamp, metadata, DELETE unregister
- TestHealthAndStats (7) - health check, stats endpoint, error handling
- TestAgentMetadata (2) - field extraction, missing fields
- TestErrorResilience (6) - connection errors, JSON decode, exception handling
- TestHTTPErrorCodeCoverage (13) - 400, 401, 403, 404, 500, 502, 503 for register/lookup
- TestAgentIDEdgeCases (21) - Unicode (14 languages: Chinese, Japanese, Korean, Arabic, Hebrew, Thai, Hindi, Cyrillic, French, Greek, emoji), boundary values, URL special chars

#### MCP Integration (37 tests)
- TestMCPRegistryInitialization (4) - URL storage, defaults, Smithery key
- TestNANDAMCPServerLookup (5) - endpoint calls, success, 404, network error, endpoint field
- TestSmitheryMCPServerLookup (4) - API key requirement, endpoint, auth header, response
- TestServerURLConstruction (4) - NANDA direct, Smithery with API key, base64 config
- TestUnifiedServerLookup (3) - routing to NANDA/Smithery, unknown provider
- TestAgentRegistryConfigLookup (4) - endpoint, params, config parsing, error handling
- TestMCPRegistryEdgeCases (5) - timeout, invalid JSON, empty config, chained lookups, case sensitivity
- TestMCPClientResultParsing (8) - dict results, list results, string results, JSON formatting

#### Framework Adapter Bridge (71 tests)
- TestNANDAInitialization (3) - required params, optional params, defaults
- TestBridgeCreation (6) - agent_id passing, registry_url, MCP config, smithery key, message handling
- TestRegistryRegistration (12) - POST endpoint, body construction, timeout, HTTP 4xx/5xx errors (7 codes), connection error, timeout error
- TestServerLifecycle (7) - start with registration, start without, URL validation, run_server params, stop cleanup
- TestTelemetryIntegration (3) - disable behavior, flag storage, import failure handling
- TestInputValidation (6) - empty agent_id, whitespace, long ID, empty URL, lambda, class method
- TestEdgeCases (34) - 7 agent_id formats, 12 unicode formats (Korean, Arabic, Hebrew, Thai, Hindi, etc.), 7 port values, 6 URL formats

### Test Quality Improvements Applied
- All 407 tests have **Expected/Got/Cause/Fix** error message format
- Comprehensive HTTP error code coverage (400, 401, 403, 404, 500, 502, 503)
- Unicode coverage across **all test files** with 12 languages:
  - East Asian: Chinese, Japanese, Korean
  - RTL scripts: Arabic, Hebrew
  - South Asian: Thai, Hindi (Devanagari)
  - European: Cyrillic, French, Greek
  - Special: Emoji, Arabic/Japanese punctuation
- Boundary value testing (empty, whitespace, 1000-char IDs)

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

# Run all integration tests
pytest tests/integration/ -v

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_protocol_router.py -v

# Run with coverage
pytest tests/ --cov=nanda_core --cov-report=html

# Run fast (no coverage)
pytest tests/ --no-cov
```

---

## Remaining Work

### ✅ Completed
- [x] Unit Tests - 175 tests across 5 files
- [x] Integration Tests - 232 tests across 4 files
- [x] Error message quality (Expected/Got/Cause/Fix format)
- [x] HTTP error code coverage (400, 401, 403, 404, 500, 502, 503)
- [x] Unicode/edge case coverage (12 languages including RTL scripts across all test files)

### 🎯 Priority 1: Contract Tests (NEXT)
1. Create `tests/contract/` directory structure
2. Implement A2A spec compliance tests
   - AgentCard JSON schema validation
   - JSON-RPC 2.0 message format validation
   - Required fields presence
3. Implement SLIM protocol compliance tests
   - SLIM message structure validation
   - Protocol envelope format
4. Implement x402 header validation tests
   - Payment header format
   - Required header fields

### Priority 2: E2E Tests
1. Create `tests/e2e/` directory structure
2. Set up Docker Compose for test environment
3. Implement multi-agent scenario tests
4. Implement agent discovery tests
5. Implement cross-framework tests

### Priority 3: Performance Tests
1. Create `tests/performance/` directory structure
2. Implement large-scale agent tests
3. Implement message throughput tests
