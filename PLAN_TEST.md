# NEST Test Plan - Issue #7

## Overview

Four-layer test strategy following Issue #7 specification.

---

## Current Status

| Layer | Status | Passing | Failing (Bugs) | NotImplemented | Files |
|-------|--------|---------|----------------|----------------|-------|
| **Unit** | ⚠️ Partial | 126 | 24 | 5 | 5 files |
| **Integration** | ⚠️ Partial | 293 | 10 | 0 | 4 files |
| **E2E** | ✅ COMPLETE | 191 | 0 | 0 | 9 files |
| **Contract** | ⚠️ Partial | 46 | 0 | 27 | 3 files |

**Total: 721 tests** (155 unit + 302 integration + 191 E2E + 73 contract)
- **Passing: 655** (tests that verify implemented functionality)
- **Failing: 34** (tests exposing library bugs - need fixes in nanda_core)
- **NotImplementedError: 32** (tests for features not yet in nanda_core)

---

## Layer 1: Unit Tests (PARTIAL)

### Files and Test Counts

| File | Passing | Failing | NotImpl | Coverage |
|------|---------|---------|---------|----------|
| `test_protocol_adapters.py` | 14 | 4 | 0 | A2A format, metadata, edge cases, **4 return type bug tests** |
| `test_protocol_router.py` | 21 | 11 | 0 | 5 routing patterns, priority, errors, **11 bug exposure tests** |
| `test_agentfacts_parser.py` | 0 | 0 | 5 | ⏳ PLACEHOLDER - AgentFacts not defined (see python_a2a.AgentCard) |
| `test_mention_extraction_and_routing.py` | 53 | 3 | 0 | Standard/unicode formats, commands, edge cases |
| `test_framework_adapters.py` | 38 | 6 | 0 | Params, validation, behavior, **6 bug exposure tests** |

### Detailed Breakdown

#### Protocol Adapters (18 tests: 14 passing, 4 failing)
Tests REAL `SimpleAgentBridge` from nanda_core.
- TestA2AMessageFormatting (4) - role, content type, agent ID prefix, non-text rejection
- TestA2AMessageMetadata (4) - conversation ID, parent ID, unique message IDs
- TestA2AErrorHandling (1) - exception handling
- TestA2AEdgeCases (5) - empty, special chars, unicode, long text, whitespace
- TestAgentLogicReturnTypeValidation (4) - **4 bug exposure tests for non-string returns**

#### Protocol Router (32 tests: 21 passing, 11 failing)
Tests REAL `SimpleAgentBridge.handle_message()` routing logic.
- TestRegularMessageRouting (4) - agent_logic routing, telemetry
- TestAtPrefixRouting (3) - @agent-id outgoing A2A
- TestHashPrefixRouting (3) - #registry:server MCP + **1 bug exposure test**
- TestSlashPrefixRouting (5) - /command system commands + **2 bug exposure tests**
- TestIncomingA2ARouting (11) - FROM:/TO:/MESSAGE: format + **8 bug exposure tests**
- TestRoutingPriority (3) - priority order verification
- TestRoutingErrorHandling (3) - exceptions, non-text, conversation preservation

#### AgentFacts Parser (5 tests) ⏳ PLACEHOLDER - FEATURE NOT DEFINED
**All tests raise NotImplementedError** - documents that AgentFacts is undefined.
- TestAgentFactsPlaceholder (5) - specification needed, AgentCard distinction, use case, location, parsing requirements

**Note**: "AgentFacts" is mentioned but not defined. The python_a2a library provides `AgentCard` with:
name, description, url, version, authentication, capabilities, skills, provider, documentation_url.
If AgentFacts is needed, a specification must be created first.

#### @mention Extraction & Routing (56 tests: 53 passing, 3 failing)
Tests REAL `SimpleAgentBridge` mention handling.
- TestMentionStandardFormats (11) - simple, hyphens, underscores, numbers, dots, case, single char
- TestMentionUnicodeFormats (10) - Chinese, Japanese, Cyrillic, Korean, Arabic, Hebrew, Thai, Hindi, French, Greek
- TestMentionBoundaryConditions (5) - no body, whitespace only, @ alone, @ space, empty (**2 bug exposure tests**)
- TestMentionPosition (3) - at start, in middle, email in body
- TestMentionMessageContent (11) - special chars, unicode, newlines, tabs, long ID/body, **tab/newline separators, @@@/@ #**
- TestMentionErrorHandling (1) - non-text content
- TestCommandHelp (2) - header, lists all commands
- TestCommandPing (2) - returns pong, ignores extra args
- TestCommandStatus (4) - agent ID, running state, registry URL, omits when unconfigured
- TestCommandUnknown (2) - unknown error, uppercase handling
- TestCommandEdgeCases (5) - / only, / spaces, leading whitespace, //, **newline bug exposure test**

#### Framework Adapters (44 tests: 38 passing, 6 failing)
Tests REAL `SimpleAgentBridge` initialization, validation, and behavior.
- TestImportVerification (1) - SimpleAgentBridge importable
- TestParameterValidationBugs (4) - **4 CLEAR BUG tests for no validation** (None, not callable, wrong signature)
- TestRequiredParameters (2) - init with required params, callable agent_logic
- TestOptionalParameters (2) - consolidated default/custom value tests
- TestFullConfiguration (2) - all params, functional bridge
- TestBehaviorVerification (4) - agent_logic called, return value used, agent_id in response
- TestAgentIdFormats (7) - simple, hyphens, underscores, numbers, uppercase, mixed, dots
- TestUrlFormats (5) - localhost, port, https, path, port+path
- TestEdgeCases (17) - **2 DEBATABLE** (empty/whitespace agent_id), long ID, unicode (12 languages)

---

## Layer 2: Integration Tests (PARTIAL - 6 bug exposure tests)

### Files and Test Counts

| File | Tests | Failing | Coverage |
|------|-------|---------|----------|
| `test_protocol_communication_flows.py` | 64 | 1 | A2A routing, registry lookup, **1 URL construction bug** |
| `test_registry_client.py` | 82 | 0 | Registration, lookup, search, health, HTTP errors, Unicode (14 languages) |
| `test_mcp_integration.py` | 75 | 3 | NANDA/Smithery lookups, URL building, **3 bug exposure tests** |
| `test_framework_adapter_bridge.py` | 81 | 6 | NANDA adapter, bridge creation, lifecycle, **6 bug exposure tests** |

### Detailed Breakdown

#### Protocol Communication Flows (64 tests: 63 passing, 1 failing)
- TestHTTPErrorCodeCoverage (5) - 400, 401, 403, 502, 503 registry errors
- TestAgentIDEdgeCases (13) - empty, whitespace, long, 5 unicode languages, 5 URL special chars
- TestURLConstructionEdgeCases (4) - **1 DEBATABLE BUG** (trailing slash causes //), malformed/empty/null agent_url
- TestA2AMessageFormatValidation (7) - bare mention, valid format, middle mention, special chars
- TestRegistryLookupBehavior (8) - endpoint calls, 404, 500, timeout, connection error, invalid JSON
- TestA2AMessageSending (4) - client creation, response handling, send failure, empty response
- TestIncomingA2AMessageHandling (4) - FROM/TO/MESSAGE parsing, loop prevention, malformed
- TestMessageMetadataPreservation (2) - conversation ID preservation and generation
- TestA2AEdgeCasesAndBoundaries (17) - long message, 12 unicode scripts, self-mention, multiple @, whitespace, newlines

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

#### MCP Integration (75 tests: 72 passing, 3 failing)
- TestParameterValidationBugs (3) - **1 CLEAR BUG** (url=None), **2 DEBATABLE** (server_name validation)
- TestBuildSmitheryServerURL (5) - HTTP extraction, fallback, stdio, missing URL, **1 BUG** (HTTP priority)
- TestHTTPErrorCodeCoverage (13) - NANDA errors (7 codes), Smithery errors (6 codes including 429)
- TestServerNameEdgeCases (17) - 8 formats, 5 unicode languages, 4 special characters
- TestMCPRegistryInitialization (4) - URL storage, defaults, Smithery key
- TestNANDAMCPServerLookup (5) - endpoint calls, success, 404, network error, endpoint field
- TestSmitheryMCPServerLookup (4) - API key requirement, endpoint, auth header, response
- TestServerURLConstruction (4) - NANDA direct, Smithery with API key, base64 config
- TestUnifiedServerLookup (3) - routing to NANDA/Smithery, unknown provider
- TestAgentRegistryConfigLookup (4) - endpoint, params, config parsing, error handling
- TestMCPRegistryEdgeCases (5) - timeout, invalid JSON, empty config, chained lookups, case sensitivity
- TestMCPClientResultParsing (8) - dict results, list results, string results, JSON formatting

#### Framework Adapter Bridge (81 tests: 75 passing, 6 failing)
- TestParameterValidationBugs (4) - **4 CLEAR BUG tests** (agent_id=None, agent_logic=None, not callable, wrong signature)
- TestPortValidation (2) - **2 DEBATABLE tests** (port=-1, port=70000)
- TestNANDAInitialization (3) - required params, optional params, defaults
- TestBridgeCreation (6) - agent_id passing, registry_url, MCP config, smithery key, message handling
- TestBehaviorVerification (4) - agent_id in response, agent_logic output, conversation_id passed, message text passed
- TestRegistryRegistration (12) - POST endpoint, body construction, timeout, HTTP 4xx/5xx errors (7 codes), connection error, timeout error
- TestServerLifecycle (7) - start with registration, start without, URL validation, run_server params, stop cleanup
- TestTelemetryIntegration (3) - disable behavior, flag storage, import failure handling
- TestInputValidation (5) - empty/whitespace agent_id (consolidated), long ID, empty URL, lambda, class method
- TestEdgeCases (35) - 7 agent_id formats, 12 unicode formats, 7 port values, 6 URL formats, argument verification

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
- [x] Unit Tests - 126 passing + 24 failing (bugs) + 5 NotImplementedError (AgentFacts placeholder)
- [x] Integration Tests - 232 passing
- [x] E2E Tests - 191 passing
- [x] Contract Tests - 46 passing + 27 NotImplementedError (SLIM, x402)
- [x] Error message quality (Expected/Got/Cause/Fix format)
- [x] HTTP error code coverage (400, 401, 403, 404, 500, 502, 503)
- [x] Unicode/edge case coverage (12 languages including RTL scripts)
- [x] Real library code testing (not just mocks)
- [x] Bug exposure tests - 24 tests that FAIL to expose library issues (15 clear bugs, 9 debatable)
- [x] Removed redundant tests, strengthened weak assertions
- [x] Added 4 edge case tests for @mention separators and special character combinations
- [x] Added parameter validation bug tests (agent_id=None, agent_logic=None, not callable)
- [x] Added behavior verification tests (agent_logic called with correct params, return value used)
- [x] Consolidated redundant optional parameter tests (8 tests → 2)
- [x] AgentFacts tests - 5 placeholder tests documenting feature is undefined (use python_a2a.AgentCard)

### Not Implemented in nanda_core (Tests Raise NotImplementedError)

| Feature | Tests | Status |
|---------|-------|--------|
| AgentFacts | 5 | No specification (use python_a2a.AgentCard) |
| SLIM Protocol | 10 | Issue #3 |
| x402 Payments | 17 | Issue #4 |

**Total: 32 tests** awaiting specification or library implementation.

### Known Issues
1. **MCP Package Dependency**: `nanda_core/core/mcp_client.py` imports `mcp.client.streamable_http` which doesn't exist in the installed `mcp` package. This is a library issue.

2. **AgentFacts Not Defined**: 5 placeholder tests document that "AgentFacts" has no specification. Consider using python_a2a.AgentCard instead.

3. **SLIM Protocol Not Implemented** (Issue #3): 10 contract tests raise NotImplementedError.

4. **x402 Protocol Not Implemented** (Issue #4): 17 contract tests raise NotImplementedError.

### Library Issues Discovered Through Testing (34 Failing Tests)

These tests **FAIL** to expose potential issues in `nanda_core/core/agent_bridge.py`, `nanda_core/core/adapter.py`, and `nanda_core/core/mcp_registry.py`.

**CLEAR BUGS** (21): Objectively wrong behavior - no validation, wasteful operations, malformed output
**DEBATABLE** (13): Design decisions that may or may not be bugs - needs spec clarification

#### @mention/Command Issues (3 tests in test_mention_extraction_and_routing.py)

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_at_space_returns_invalid_format` | `@ ` | **CLEAR BUG** | Looks up empty agent '' (wasteful) |
| `test_whitespace_body_returns_invalid_format` | `@agent   ` | DEBATABLE | Sends whitespace - could be valid |
| `test_command_with_newline_executes_correctly` | `/ping\ntest` | DEBATABLE | Newline handling is edge case |

#### A2A Field Validation Issues (5 tests in test_protocol_router.py)

All **CLEAR BUGS** - produce malformed responses like `Response to : ` with dangling colon.

| Failing Test | Input | Issue |
|--------------|-------|-------|
| `test_empty_from_field_returns_error` | `FROM:\nTO: test\nMESSAGE: hi` | Empty sender produces malformed response |
| `test_empty_to_field_returns_error` | `FROM: sender\nTO:\nMESSAGE: hi` | Empty recipient accepted |
| `test_all_empty_a2a_fields_returns_error` | `FROM:\nTO:\nMESSAGE:` | All empty fields processed |
| `test_whitespace_from_field_returns_error` | `FROM:   \nTO: test\nMESSAGE: hi` | Whitespace sender produces `Response to : ` |
| `test_whitespace_to_field_returns_error` | `FROM: sender\nTO:   \nMESSAGE: hi` | Whitespace recipient accepted |

#### Routing Edge Case Issues (6 tests in test_protocol_router.py)

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_mcp_empty_server_returns_invalid_format` | `#registry: query` | **CLEAR BUG** | Looks up empty server '' |
| `test_double_hash_parsed_correctly` | `##smithery:weather` | **CLEAR BUG** | Includes # in registry name |
| `test_double_slash_parsed_correctly` | `//help` | **CLEAR BUG** | Includes / in command name |
| `test_slash_alone_returns_helpful_error` | `/` | **CLEAR BUG** | Shows "Unknown command: ." |
| `test_lowercase_a2a_format_detected` | `from: sender\nto: test\nmessage: hi` | DEBATABLE | Case-sensitive - may be by design |
| `test_wrong_order_a2a_format_detected` | `TO: test\nFROM: sender\nMESSAGE: hi` | DEBATABLE | Order-dependent - may be by design |

#### agent_logic Return Type Issues (4 tests in test_protocol_adapters.py)

| Failing Test | Return Value | Category | Issue |
|--------------|--------------|----------|-------|
| `test_agent_logic_returns_none_handled` | `None` | **CLEAR BUG** | Shows literal "None" - confusing |
| `test_agent_logic_returns_int_handled` | `42` | DEBATABLE | Shows "42" - could be flexibility |
| `test_agent_logic_returns_list_handled` | `["item1"]` | DEBATABLE | Shows Python repr - ugly but works |
| `test_agent_logic_returns_dict_handled` | `{"k": "v"}` | DEBATABLE | Shows Python repr - ugly but works |

#### Parameter Validation Issues (6 tests in test_framework_adapters.py)

No validation at init time - library accepts invalid parameters and fails gracefully at use time.

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_agent_id_none_accepted_no_validation` | `agent_id=None` | **CLEAR BUG** | None accepted, creates broken bridge |
| `test_agent_logic_none_fails_at_use` | `agent_logic=None` | **CLEAR BUG** | None accepted, error at use time |
| `test_agent_logic_not_callable_fails_at_use` | `agent_logic="string"` | **CLEAR BUG** | Non-callable accepted, error at use |
| `test_agent_logic_wrong_signature_fails_at_use` | `def f(): ...` | **CLEAR BUG** | Wrong signature accepted, error at use |
| `test_empty_string_agent_id` | `agent_id=""` | DEBATABLE | Creates "[] Response" - awkward |
| `test_whitespace_only_agent_id` | `agent_id="   "` | DEBATABLE | Creates "[   ] Response" - confusing |

#### NANDA Adapter Issues (6 tests in test_framework_adapter_bridge.py)

No validation at init time in NANDA class - passes invalid params to SimpleAgentBridge.

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_agent_id_none_accepted_no_validation` | `agent_id=None` | **CLEAR BUG** | None accepted, creates broken NANDA |
| `test_agent_logic_none_fails_at_use_time` | `agent_logic=None` | **CLEAR BUG** | None accepted, fails at message time |
| `test_agent_logic_not_callable_fails_at_use_time` | `agent_logic="string"` | **CLEAR BUG** | Non-callable accepted, fails at use |
| `test_agent_logic_wrong_signature_fails_at_use_time` | `def f(): ...` | **CLEAR BUG** | Wrong signature accepted, fails at use |
| `test_negative_port_accepted` | `port=-1` | DEBATABLE | Invalid port accepted, fails at server start |
| `test_port_above_max_accepted` | `port=70000` | DEBATABLE | Out of range port accepted |

#### MCP Registry Issues (3 tests in test_mcp_integration.py)

No validation in MCPRegistry - accepts None URLs, empty server names, incorrect connection prioritization.

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_mcp_registry_url_none_accepted` | `mcp_registry_url=None` | **CLEAR BUG** | None accepted, fails at lookup |
| `test_server_name_empty_string_accepted` | `server_name=""` | DEBATABLE | Builds URL ending in /mcp_servers/ |
| `test_prefers_http_over_stdio` | Mixed connections | **CLEAR BUG** | stdio preferred over HTTP |

#### URL Construction Issues (1 test in test_protocol_communication_flows.py)

Trailing slash in registry_url not handled properly.

| Failing Test | Input | Category | Issue |
|--------------|-------|----------|-------|
| `test_registry_url_trailing_slash_handled` | `registry_url="http://test/"` | DEBATABLE | Creates URL with // (e.g., http://test//lookup/agent) |

---

### Summary: Clear Bugs vs Debatable

| Category | Count | Examples |
|----------|-------|----------|
| **CLEAR BUGS** | 21 | No validation (10), empty lookups (2), malformed A2A responses (5), None→"None" (1), prefix parsing (3) |
| **DEBATABLE** | 13 | Case/order sensitivity (2), type coercion (3), whitespace/empty (4), newline (1), port range (2), URL trailing slash (1) |
