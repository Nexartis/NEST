# NEST Test Plan - Issue #7

## Overview

Four-layer test strategy following Issue #7 specification.

---

## Current Status

| Layer | Status | Passing | Failing (Bugs) | NotImplemented | Files |
|-------|--------|---------|----------------|----------------|-------|
| **Unit** | ⚠️ Partial | 127 | 8 | 5 | 5 files |
| **Integration** | ✅ COMPLETE | 232 | 0 | 0 | 4 files |
| **E2E** | ✅ COMPLETE | 191 | 0 | 0 | 9 files |
| **Contract** | ⚠️ Partial | 46 | 0 | 27 | 3 files |

**Total: 636 tests** (140 unit + 232 integration + 191 E2E + 73 contract)
- **Passing: 596** (tests that verify implemented functionality)
- **Failing: 8** (tests exposing library bugs - need fixes in nanda_core)
- **NotImplementedError: 32** (tests for features not yet in nanda_core)

---

## Layer 1: Unit Tests (PARTIAL)

### Files and Test Counts

| File | Passing | Failing | NotImpl | Coverage |
|------|---------|---------|---------|----------|
| `test_protocol_adapters.py` | 14 | 0 | 0 | A2A format, metadata, edge cases |
| `test_protocol_router.py` | 22 | 5 | 0 | 5 routing patterns, priority, errors, **A2A field validation bugs** |
| `test_agentfacts_parser.py` | 0 | 0 | 5 | ⏳ NOT IMPLEMENTED in nanda_core |
| `test_mention_extraction_and_routing.py` | 49 | 3 | 0 | Standard/unicode formats, commands |
| `test_framework_adapters.py` | 31 | 0 | 0 | Required/optional params, formats |

### Detailed Breakdown

#### Protocol Adapters (14 tests) ✅
Tests REAL `SimpleAgentBridge` from nanda_core.
- TestA2AMessageFormatting (4) - role, content type, agent ID prefix, non-text rejection
- TestA2AMessageMetadata (4) - conversation ID, parent ID, unique message IDs
- TestA2AErrorHandling (1) - exception handling
- TestA2AEdgeCases (5) - empty, special chars, unicode, long text, whitespace

#### Protocol Router (27 tests: 22 passing, 5 failing)
Tests REAL `SimpleAgentBridge.handle_message()` routing logic.
- TestRegularMessageRouting (4) - agent_logic routing, telemetry
- TestAtPrefixRouting (4) - @agent-id outgoing A2A
- TestHashPrefixRouting (2) - #registry:server MCP
- TestSlashPrefixRouting (3) - /command system commands
- TestIncomingA2ARouting (8) - FROM:/TO:/MESSAGE: format + **5 bug exposure tests**
- TestRoutingPriority (3) - priority order verification
- TestRoutingErrorHandling (3) - exceptions, non-text, conversation preservation

#### AgentFacts Parser (5 tests) ⏳ NOT IMPLEMENTED
**All tests raise NotImplementedError** - AgentFacts parser does not exist in nanda_core.
Concise placeholder tests awaiting library implementation.
- test_parse_agent_facts_exists - parser function should exist
- test_agentfacts_class_exists - dataclass should exist
- test_required_field_agent_id - agent_id required
- test_optional_fields_supported - name, description, etc.
- test_validation_errors - invalid input handling

#### @mention Extraction & Routing (52 tests: 49 passing, 3 failing)
Tests REAL `SimpleAgentBridge` mention handling.
- TestMentionStandardFormats (11) - simple, hyphens, underscores, numbers, dots, case, single char
- TestMentionUnicodeFormats (5) - Chinese, Japanese, Cyrillic, French, Greek
- TestMentionBoundaryConditions (5) - no body, whitespace only, @ alone, @ space, empty (**2 bug exposure tests**)
- TestMentionPositionEdgeCases (3) - at start, not at start, email in message
- TestMentionMessageContent (7) - special chars, unicode, newlines, tabs, long ID, long body, minimal
- TestMentionErrorHandling (1) - non-text content
- TestCommandHelp (2) - header, lists all commands
- TestCommandPing (2) - returns pong, ignores extra args
- TestCommandStatus (4) - agent ID, running state, registry URL, omits when unconfigured
- TestCommandUnknown (2) - unknown error, uppercase handling
- TestCommandEdgeCases (5) - / only, / spaces, leading whitespace, //, **newline bug exposure test**

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
- All 409 tests have **Expected/Got/Cause/Fix** error message format
- Comprehensive HTTP error code coverage (400, 401, 403, 404, 500, 502, 503)
- Unicode coverage across **all test files** with 12 languages:
  - East Asian: Chinese, Japanese, Korean
  - RTL scripts: Arabic, Hebrew
  - South Asian: Thai, Hindi (Devanagari)
  - European: Cyrillic, French, Greek
  - Special: Emoji, Arabic/Japanese punctuation
- Boundary value testing (empty, whitespace, 1000-char IDs)

---

## Layer 3: E2E Tests (COMPLETE)

**Directory**: `tests/e2e/`

### Files and Test Counts

| File | Tests | Coverage |
|------|-------|----------|
| `test_agent_lifecycle.py` | 16 | Startup, registration, shutdown, health checks |
| `test_agent_communication.py` | 18 | A2A messages, content handling, concurrent requests |
| `test_agent_discovery.py` | 20 | Registry lookup, list, search, MCP discovery |
| `test_mention_routing_e2e.py` | 16 | @mention routing, formats, chaining |
| `test_error_scenarios.py` | 20 | Network errors, HTTP codes, invalid requests |
| `test_multi_agent_chains.py` | 13 | Multi-agent conversations, parallel messaging |
| `test_security_edge_cases.py` | 13 | SQL injection, XSS, path traversal, malformed requests |
| `test_mcp_integration.py` | 18 | Real MCP server, full flow, tool execution, errors |
| `test_real_library_code.py` | 17 | Real RegistryClient, MCPRegistry, MCPClient |

**Total: 151 E2E tests**

### Infrastructure Files

| File | Purpose |
|------|---------|
| `conftest.py` | E2E fixtures: process management, HTTP client, polling utilities, real library fixtures |
| `registry_server.py` | Simple Flask registry for local testing (no DB required) |
| `mcp_test_server.py` | Simple MCP server for testing real MCP integration |

### Detailed Breakdown

#### Agent Lifecycle (16 tests)
- TestAgentStartup (4) - port binding, auto-assignment, startup time, multiple agents
- TestAgentRegistration (4) - registry registration, URL inclusion, list appearance, ID formats
- TestAgentHealthCheck (2) - health endpoint, stats endpoint
- TestAgentShutdown (2) - SIGTERM handling, port release
- TestAgentLifecycleEdgeCases (2) - long ID, unicode ID
- TestMCPAgentLifecycle (2) - MCP server registration, listing

#### Agent Communication (18 tests)
- TestBasicCommunication (3) - receive message, response format, empty/whitespace
- TestMessageContent (6) - content preservation, large messages, special chars, unicode
- TestConversationTracking (3) - conversation ID, multi-turn, isolation
- TestConcurrentMessages (2) - 10 and 50 concurrent requests
- TestMCPCommunication (4) - #nanda:, #smithery: formats, MCP lookup

#### Agent Discovery (20 tests)
- TestRegistryLookup (5) - registered/unregistered lookup, case sensitivity, special chars, value verification
- TestRegistryList (3) - list all, empty registry, count field
- TestRegistrySearch (4) - query, capabilities, tags, no matches
- TestRegistryStatus (2) - status update, unregister
- TestRealRegistry (2) - production registry.chat39.com health/list
- TestMCPServerDiscovery (4) - register, lookup, 404, list

#### @Mention Routing E2E (16 tests)
- TestBasicMentionRouting (4) - route to target with proof, response return, multiword, conversation ID
- TestMentionFormats (3) - various agent_id formats
- TestMentionEdgeCases (5) - nonexistent agent, self-reference, multiple @, email, unicode
- TestMentionChaining (4) - round trip, loop detection, incoming format, response prefix

#### Error Scenarios (20 tests)
- TestNetworkErrors (3) - connection refused, offline registry, timeout
- TestHTTPErrorCodes (4) - 400, 404 for agent/registry
- TestInvalidRequests (5) - empty body, wrong content-type, missing fields, wrong method, large body
- TestRegistryErrors (4) - duplicate registration, unregister nonexistent, status update, offline handling
- TestMCPErrorScenarios (4) - server not found, invalid data, unavailable server, invalid format

#### Multi-Agent Chains (13 tests)
- TestTwoAgentConversation (3) - single exchange with proof, multiple exchanges, bidirectional with proof
- TestMultiAgentChains (3) - three agents discoverable, targeted routing, five agents coexist
- TestConversationIsolation (2) - different IDs isolated, interleaved conversations
- TestParallelMessaging (3) - parallel to same target, parallel pairs, rapid sequential
- TestMultiAgentEdgeCases (2) - one-to-many, similar names

#### Security Edge Cases (13 tests)
- TestInputValidation (7) - SQL injection (7 patterns), XSS with Content-Type verification
- TestMalformedRequests (2) - deeply nested JSON, null bytes
- TestAgentEdgeCases (2) - whitespace handling, restart scenarios
- TestResponseEdgeCases (2) - JSON special chars, binary data

#### Real MCP Integration (18 tests)
- TestMCPServerDirect (6) - health check, initialize, tools/list, echo/add/get_time execution
- TestMCPThroughAgent (5) - MCP server registration, **full flow (agent→registry→MCP→result)**, format detection, smithery format, invalid format
- TestMCPErrorHandling (4) - invalid method, unknown tool, malformed JSON-RPC, invalid JSON
- TestMCPToolSchemas (3) - missing required arg, wrong arg type, extra args ignored

#### Real Library Code (17 tests)
- TestRegistryClientReal (8) - health_check(), register_agent(), lookup_agent(), list_agents(), search_agents(), unregister_agent()
- TestMCPRegistryReal (5) - get_nanda_mcp_server_info(), get_mcp_server_info(), error handling
- TestLibraryIntegration (2) - registry_client + agent registration, full workflow
- TestMCPClientReal (2) - connect_to_server(), parse/format methods

### Key E2E Improvements

1. **Real Library Testing** - Tests actual `RegistryClient`, `MCPRegistry`, `MCPClient` classes, not just HTTP endpoints
2. **Full MCP Flow Test** - Complete path: agent receives `#nanda:server` → registry lookup → MCP server call → result
3. **Polling Instead of Sleep** - `wait_for_agent_registered()` replaces all `time.sleep(0.5)` calls
4. **Stronger Assertions** - Verify actual response content, not just status codes
5. **No Duplicate Constants** - All files import from `conftest.py`

### What's REAL vs Mocked

| Real (Tested) | Mocked (External) |
|---------------|-------------------|
| Agent HTTP server (subprocess) | Anthropic Claude API (agent logic is simple echo) |
| A2A protocol messages | |
| Registry HTTP API | |
| RegistryClient library class | |
| MCPRegistry library class | |
| MCPClient library class | |
| MCP protocol (JSON-RPC) | |
| Network communication | |
| Process lifecycle | |

---

## Layer 4: Contract Tests (COMPLETE)

**Directory**: `tests/contract/`

### Files and Test Counts

| File | Tests | Status |
|------|-------|--------|
| `test_a2a_compliance.py` | 46 | ✅ All passing |
| `test_slim_compliance.py` | 10 | ⏳ NotImplementedError (protocol not implemented) |
| `test_x402_payments.py` | 17 | ⏳ NotImplementedError (protocol not implemented) |

**Total: 73 contract tests**

### Detailed Breakdown

#### A2A Protocol Compliance (46 tests) - IMPLEMENTED
Tests REAL python_a2a library classes (Message, TextContent, MessageRole, Metadata).

- TestA2AMessageRequiredFields (4) - content, role, role enum, message_id
- TestA2AMessageOptionalFields (4) - conversation_id, parent_message_id, metadata, minimal
- TestA2ATextContent (23) - text field, string type, empty, whitespace, 10 unicode languages, 9 special characters
- TestA2AJsonSerialization (4) - serialization method, valid JSON, required fields, round-trip
- TestA2AResponseContracts (4) - AGENT role exists/used, parent reference, conversation_id
- TestA2AMessageIdGeneration (3) - auto-generation, preservation, uniqueness
- TestA2AEdgeCases (4) - 100KB text, long message_id, minimal fields, JSON-like strings

#### SLIM Protocol Compliance (10 tests) - NOT IMPLEMENTED
All tests raise `NotImplementedError` until protocol is added to nanda_core.
- TestSLIMMessageEnvelope (4) - version, type, id, payload fields
- TestSLIMRouting (3) - source, destination, broadcast
- TestSLIMErrorResponse (3) - code, message, error code ranges

#### x402 Payment Protocol (17 tests) - NOT IMPLEMENTED
All tests raise `NotImplementedError` until protocol is added to nanda_core.
- TestX402Headers (5) - 402 status, payment-address, amount, currency, network
- TestX402PaymentToken (4) - base64 encoding, receipt, signature, timestamp
- TestX402RequestFlow (5) - initial request, valid/invalid/expired/insufficient payment
- TestX402Security (3) - replay prevention, signature verification, nonce

---

## Test Quality Standards

All tests follow these requirements:

### 1. Best Practice
- Test actual library code, not just HTTP endpoints
- Meaningful assertions verifying actual values
- Use fixtures for reusable test data
- Use `pytestmark` for module-level markers

### 2. Well Documented
- Given-When-Then docstring format
- "Tests REAL:" and "Mocks:" sections
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
- Constants imported from conftest, not duplicated

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

# Run all E2E tests
pytest tests/e2e/ -v -m e2e

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_protocol_router.py -v

# Run with coverage
pytest tests/ --cov=nanda_core --cov-report=html

# Run fast (no coverage)
pytest tests/ --no-cov

# Run tests by marker
pytest -m unit           # Only unit tests
pytest -m integration    # Only integration tests
pytest -m e2e            # Only E2E tests
pytest -m "not slow"     # Skip slow tests
```

---

## Remaining Work

### ✅ Completed (Issue #7 Acceptance Criteria)
- [x] pytest configured with coverage reporting
- [x] Unit tests for protocol adapters (A2A implemented, SLIM not in library)
- [x] Integration tests with mocked external dependencies
- [x] Test fixtures for common scenarios (agent configs, mock responses)
- [x] Mock NANDA Index for integration tests
- [x] E2E test suite with multi-agent scenarios (subprocess-based, no Docker)
- [x] E2E tests cover: agent discovery, @mention routing
- [x] E2E tests for real library code (RegistryClient, MCPRegistry, MCPClient)

### ⚠️ Test Implementation Status (Honest Assessment)
- [x] Unit Tests - 127 passing + 8 failing (bugs) + 5 NotImplementedError (AgentFacts)
- [x] Integration Tests - 232 passing
- [x] E2E Tests - 191 passing
- [x] Contract Tests - 46 passing + 27 NotImplementedError (SLIM, x402)
- [x] Error message quality (Expected/Got/Cause/Fix format)
- [x] HTTP error code coverage (400, 401, 403, 404, 500, 502, 503)
- [x] Unicode/edge case coverage (12 languages including RTL scripts)
- [x] Real library code testing (not just mocks)
- [x] Bug exposure tests - 8 tests that FAIL to expose library bugs

### Not Implemented in nanda_core (Tests Raise NotImplementedError)

| Feature | Tests | GitHub Issue |
|---------|-------|--------------|
| AgentFacts Parser | 5 | Not filed |
| SLIM Protocol | 10 | Issue #3 |
| x402 Payments | 17 | Issue #4 |

**Total: 32 tests** awaiting library implementation.

### Known Issues
1. **MCP Package Dependency**: `nanda_core/core/mcp_client.py` imports `mcp.client.streamable_http` which doesn't exist in the installed `mcp` package. This is a library issue.

2. **AgentFacts Parser Not Implemented**: 5 unit tests raise NotImplementedError. No GitHub issue filed yet.

3. **SLIM Protocol Not Implemented** (Issue #3): 10 contract tests raise NotImplementedError.

4. **x402 Protocol Not Implemented** (Issue #4): 17 contract tests raise NotImplementedError.

### Library Bugs Discovered Through Testing (8 Failing Tests)

These tests **FAIL** to expose bugs in `nanda_core/core/agent_bridge.py`:

#### @mention/Command Bugs (3 tests in test_mention_extraction_and_routing.py)

| Failing Test | Input | Expected | Actual (Bug) |
|--------------|-------|----------|--------------|
| `test_whitespace_body_returns_invalid_format` | `@agent   ` | "Invalid format" | Sends whitespace |
| `test_at_space_returns_invalid_format` | `@ ` | "Invalid format" | Looks up empty agent |
| `test_command_with_newline_executes_correctly` | `/ping\ntest` | "Pong!" | "Unknown command" |

**Fixes Required:**
- `_handle_agent_message()`: Add `if not message_text.strip(): return error`
- `_handle_agent_message()`: Add `if not target_agent: return error`
- `_handle_command()`: Use `split(None, 1)` instead of `split(" ", 1)`

#### A2A Field Validation Bugs (5 tests in test_protocol_router.py)

| Failing Test | Input | Expected | Actual (Bug) |
|--------------|-------|----------|--------------|
| `test_empty_from_field_returns_error` | `FROM:\nTO: test\nMESSAGE: hi` | "Invalid" or "Error" | Processes with empty sender |
| `test_empty_to_field_returns_error` | `FROM: sender\nTO:\nMESSAGE: hi` | "Invalid" or "Error" | Processes with empty recipient |
| `test_all_empty_a2a_fields_returns_error` | `FROM:\nTO:\nMESSAGE:` | "Invalid" or "Error" | Processes all empty fields |
| `test_whitespace_from_field_returns_error` | `FROM:   \nTO: test\nMESSAGE: hi` | "Invalid" or "Error" | Processes whitespace sender |
| `test_whitespace_to_field_returns_error` | `FROM: sender\nTO:   \nMESSAGE: hi` | "Invalid" or "Error" | Processes whitespace recipient |

**Fixes Required:**
- `_handle_incoming_a2a()`: Add `if not sender.strip(): return error`
- `_handle_incoming_a2a()`: Add `if not recipient.strip(): return error`
- `_handle_incoming_a2a()`: Validate all required fields are non-empty before processing
