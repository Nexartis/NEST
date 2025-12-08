# E2E Test Plan for NEST

## Overview

E2E tests exercise REAL system behavior with actual HTTP calls, subprocess management, and live registry communication. Unlike unit/integration tests that mock dependencies, E2E tests verify the complete flow.

---

## Test File Responsibilities (Clear Separation)

Each test file has a **distinct focus** to avoid duplication:

| File | Focus | Tests |
|------|-------|-------|
| `test_agent_lifecycle.py` | **Process Management** - startup, shutdown, signals, ports | 26 |
| `test_agent_discovery.py` | **Library Clients** - RegistryClient, MCPRegistry with real HTTP | 30 |
| `test_agent_communication.py` | **A2A Protocol** - message flow, routing, @mentions | ~20 |
| `test_error_scenarios.py` | **Error Handling** - graceful failures, recovery, error messages | 24 |
| `test_mcp_integration.py` | **MCP Protocol** - JSON-RPC, tools, prompts | ~30 |
| `test_mention_routing_e2e.py` | **@Mention Routing** - end-to-end mention flow | ~15 |

---

## Test File Structure

```
tests/e2e/
├── conftest.py                    # E2E fixtures (process management, timeouts)
├── registry_server.py             # Flask registry for local testing
├── test_agent_lifecycle.py        # Process: startup, shutdown, signals, ports
├── test_agent_discovery.py        # Clients: RegistryClient, MCPRegistry
├── test_agent_communication.py    # A2A: message flow, routing
├── test_error_scenarios.py        # Errors: graceful failures, recovery
├── test_mcp_integration.py        # MCP: protocol, tools, prompts
├── test_mention_routing_e2e.py    # @mentions: routing flow
└── test_multi_agent_chains.py     # Chains: A → B → C flows
```

---

## Detailed Test Categories

### 1. Agent Lifecycle Tests (`test_agent_lifecycle.py`)

**Focus:** Process/subprocess behavior, OS-level concerns

| Test Class | Purpose | Tests |
|------------|---------|-------|
| `TestAgentStartup` | Process spawning, port binding, startup timing | 5 |
| `TestAgentShutdown` | SIGTERM, SIGINT, port release, cleanup | 4 |
| `TestAgentProcessHealth` | HTTP connectivity, concurrent requests | 2 |
| `TestAgentLifecycleErrorScenarios` | Registry unavailable, port conflict, bad logic | 3 |
| `TestAgentPortManagement` | Port reuse, rapid spawning | 2 |
| `TestAgentIDEdgeCases` | Long IDs, special formats | 2 |
| `TestAgentStartupTiming` | Performance, no degradation | 2 |
| `TestProcessCleanup` | Fixture cleanup, log capture | 2 |

**Key Tests:**
- `test_agent_starts_on_specified_port` - Port binding works
- `test_agent_terminates_on_sigterm` - Signal handling
- `test_agent_starts_when_registry_unavailable` - Resilience
- `test_agent_handles_port_already_in_use` - Conflict handling

---

### 2. Agent Discovery Tests (`test_agent_discovery.py`)

**Focus:** Library client code (RegistryClient, MCPRegistry) with real HTTP

| Test Class | Purpose | Tests |
|------------|---------|-------|
| `TestRegistryClientLookup` | `RegistryClient.lookup_agent()` | 4 |
| `TestRegistryClientList` | `RegistryClient.list_agents()` | 3 |
| `TestRegistryClientSearch` | `RegistryClient.search_agents()` | 3 |
| `TestRegistryClientStatus` | Status and unregister operations | 3 |
| `TestRegistryClientErrorHandling` | Error injection (400, 500, 503) | 5 |
| `TestMCPRegistryDiscovery` | `MCPRegistry` operations | 5 |
| `TestAgentLifecycle` | Full spawn → register → discover flow | 3 |
| `TestConcurrentOperations` | Thread safety, race conditions | 2 |
| `TestUnicodeAgentIDs` | Unicode handling | 3 |
| `TestCaseSensitivity` | Case-sensitive lookups | 1 |

**Key Tests:**
- `test_lookup_registered_agent_returns_agent_data` - Uses real RegistryClient
- `test_register_handles_500_error_gracefully` - Error injection
- `test_concurrent_registrations_all_succeed` - Thread safety

---

### 3. Error Scenarios Tests (`test_error_scenarios.py`)

**Focus:** Error handling behavior, graceful failures, recovery

| Test Class | Purpose | Tests |
|------------|---------|-------|
| `TestNetworkErrors` | Connection refused, timeouts, DNS | 4 |
| `TestHTTPErrorCodes` | 400, 404, 500 handling | 4 |
| `TestInvalidRequests` | Bad JSON, wrong content-type, missing fields | 5 |
| `TestRegistryErrorResponses` | Duplicate registration, unregister, status | 4 |
| `TestAgentErrorRecovery` | Agent continues after errors | 2 |
| `TestErrorMessageQuality` | Error messages are helpful | 2 |
| `TestMCPCommunicationErrors` | MCP server unreachable | 1 |

**Key Tests:**
- `test_agent_handles_target_agent_offline_gracefully` - Offline target handling
- `test_agent_continues_after_malformed_request` - Error isolation
- `test_404_error_includes_what_was_not_found` - Error message quality

---

## Architecture: Subprocess-Based Testing

```
pytest process → spawns Registry Server (port 5xxx)
              → spawns Agent A (port 6xxx)
              → spawns Agent B (port 6xxx)
              → runs tests with REAL HTTP
              → kills all processes on cleanup
```

**Why Subprocess (not Docker):**
- No Docker dependency in CI
- Faster startup (~2s vs ~10s)
- Easier debugging (local processes)
- Works in GitHub Actions

---

## What Is REAL vs MOCKED

### REAL Components (Actually Exercised)
| Component | Why Real |
|-----------|----------|
| Agent HTTP server | Core functionality |
| A2A protocol messages | Must test real format |
| Registry HTTP API | Must test real discovery |
| RegistryClient class | Must test real client code |
| MCPRegistry class | Must test real client code |
| Network communication | Must test real latency/errors |
| Process lifecycle | Must test real startup/shutdown |

### MOCKED Components (External Dependencies)
| Component | Why Mock |
|-----------|----------|
| Anthropic Claude API | External paid service |
| External MCP servers | Can't control availability |
| Smithery API | External service |

---

## Test Quality Standards

### Naming Convention
```
test_[component]_[action]_[expected_outcome]

Examples:
- test_lookup_registered_agent_returns_agent_data
- test_agent_terminates_on_sigterm
- test_agent_continues_after_malformed_request
```

### Error Message Format
```python
assert response.status_code == 200, (
    f"Expected HTTP 200, got {response.status_code}. "
    f"Response: {response.text[:200]}. "
    f"Cause: Agent may not have started. "
    f"Fix: Check agent logs at {agent.log_file}"
)
```

### Docstring Format
```python
def test_lookup_registered_agent_returns_agent_data(self, registry_client):
    """
    Given: An agent registered in the registry
    When: Calling registry_client.lookup_agent(agent_id)
    Then: Returns dict with agent_id and agent_url

    Tests REAL: RegistryClient.lookup_agent() HTTP GET
    Validates: Response parsing, field extraction
    """
```

---

## Timeout Configuration

```python
# conftest.py constants
E2E_TIMEOUT = 30              # CI max timeout per test
PROCESS_STARTUP_TIMEOUT = 10  # Wait for process to start
HTTP_REQUEST_TIMEOUT = 5      # Individual HTTP request timeout
```

---

## Test Count Summary

| Category | File | Tests | Status |
|----------|------|-------|--------|
| Process Management | `test_agent_lifecycle.py` | 26 | ✅ Complete |
| Library Clients | `test_agent_discovery.py` | 30 | ✅ Complete |
| Error Handling | `test_error_scenarios.py` | 24 | ✅ Complete |
| A2A Communication | `test_agent_communication.py` | ~20 | Existing |
| MCP Integration | `test_mcp_integration.py` | ~30 | Existing |
| @Mention Routing | `test_mention_routing_e2e.py` | ~15 | Existing |
| Multi-Agent Chains | `test_multi_agent_chains.py` | ~10 | Existing |
| **Total** | | **~155** | |

---

## File Distinction Guide

**When adding new tests, use this guide:**

| If testing... | Add to... |
|---------------|-----------|
| Process startup/shutdown | `test_agent_lifecycle.py` |
| Signal handling (SIGTERM, SIGINT) | `test_agent_lifecycle.py` |
| Port binding/release | `test_agent_lifecycle.py` |
| RegistryClient methods | `test_agent_discovery.py` |
| MCPRegistry methods | `test_agent_discovery.py` |
| Registry lookup/list/search | `test_agent_discovery.py` |
| Network errors (connection refused) | `test_error_scenarios.py` |
| HTTP error codes (400, 404, 500) | `test_error_scenarios.py` |
| Invalid request handling | `test_error_scenarios.py` |
| Error message quality | `test_error_scenarios.py` |
| A2A message format | `test_agent_communication.py` |
| @mention routing | `test_mention_routing_e2e.py` |
| MCP JSON-RPC protocol | `test_mcp_integration.py` |
| Multi-agent chains | `test_multi_agent_chains.py` |

---

## Success Criteria

1. **All tests use REAL HTTP** - No mock HTTP libraries in E2E
2. **Tests real library code** - RegistryClient, MCPRegistry, not just mock server
3. **Clear file responsibilities** - No duplicate tests across files
4. **Process management works** - Agents start/stop cleanly
5. **Comprehensive edge cases** - Unicode, errors, timeouts
6. **Developer friendly** - Clear errors, easy debugging
7. **CI compatible** - No Docker required
8. **<30s per test** - Fast feedback

---

## Infrastructure

### Registry Server (`registry_server.py`)

Flask-based in-memory registry for E2E testing:
- `/health` - Health check
- `/register` - Register agent
- `/lookup/{agent_id}` - Lookup agent
- `/list` - List all agents
- `/unregister/{agent_id}` - Unregister agent
- `/status/{agent_id}` - Get/update status
- `/mcp_servers` - MCP server registration
- `/_set_error_mode` - Error injection for testing

### Key Fixtures (`conftest.py`)

- `registry_process` - Spawns registry server
- `agent_process_factory` - Factory to spawn agents
- `registry_client` - Real RegistryClient instance
- `mcp_registry` - Real MCPRegistry instance
- `http_client` - Requests session with retry
- `wait_for_registration` - Wait for agent to register
- `send_a2a_message` - Send A2A message to agent
