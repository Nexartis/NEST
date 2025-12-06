# E2E Test Plan for NEST

## Critical Analysis: What Makes This REAL E2E Testing?

### Problem with Current Test Fixtures
Current `conftest.py` fixtures are **all mocks**:
- `mock_registry` - In-memory dict, not real HTTP
- `mock_adapter` - Message list, not real A2A protocol
- `agent_test_harness` - Combines mocks, tests nothing real

**These test mock behavior, NOT actual system behavior.**

### What E2E Tests MUST Do
1. **Start REAL agent processes** on actual ports
2. **Make REAL HTTP requests** between agents
3. **Use REAL registry** (local or containerized)
4. **Test REAL A2A protocol** message flow
5. **Only mock external services** we can't control (Anthropic API)

---

## Architecture Decision: Subprocess vs Docker

### Option A: Subprocess-Based (RECOMMENDED for CI)
```
pytest process → spawns Agent A (port 6001)
              → spawns Agent B (port 6002)
              → spawns Registry (port 5000)
              → runs tests with real HTTP
              → kills all processes
```

**Pros:**
- No Docker dependency
- Works in GitHub Actions
- Faster startup
- Easier debugging

**Cons:**
- Port management complexity
- Process cleanup required

### Option B: Docker Compose (For local/complex scenarios)
```
docker-compose up → registry, agent-a, agent-b, agent-c
pytest → connects to running containers
docker-compose down
```

**Pros:**
- Isolated environment
- Closer to production

**Cons:**
- Slower
- Docker required in CI

### Decision: **Subprocess for core tests, Docker optional for complex scenarios**

---

## Test File Structure

```
tests/e2e/
├── conftest.py                    # E2E-specific fixtures (process management)
├── test_agent_lifecycle.py        # Agent startup, registration, shutdown
├── test_agent_communication.py    # A2A message flow between agents
├── test_agent_discovery.py        # Registry lookup and discovery
├── test_mention_routing_e2e.py    # @mention routing end-to-end
├── test_error_scenarios.py        # Network errors, timeouts, invalid agents
├── test_multi_agent_chains.py     # A → B → C message chains
└── docker-compose.yml             # Optional: for complex scenarios
```

---

## E2E Fixtures (conftest.py)

### Required Fixtures

```python
@pytest.fixture(scope="module")
def registry_server():
    """
    Start a REAL registry server process.
    Returns registry URL and cleanup function.
    """
    # Start Flask-based registry on port 5000
    # Wait for health check
    # Yield URL
    # Kill process on cleanup

@pytest.fixture(scope="function")
def agent_process():
    """
    Factory to start REAL agent processes.
    Returns function to spawn agents on specified ports.
    """
    # Spawn agent subprocess
    # Wait for HTTP readiness
    # Track for cleanup

@pytest.fixture
def http_client():
    """
    Requests session with retry and timeout config.
    For making REAL HTTP calls to agents.
    """
```

---

## Test Categories and Cases

### 1. Agent Lifecycle Tests (`test_agent_lifecycle.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_agent_starts_on_specified_port` | Agent HTTP endpoint accessible | Port 0-65535, privileged ports |
| `test_agent_registers_with_registry` | POST /register actually called | Registry down, timeout, 4xx/5xx |
| `test_agent_responds_to_health_check` | GET /health returns 200 | Under load, after errors |
| `test_agent_graceful_shutdown` | Process terminates cleanly | SIGTERM, SIGKILL, timeout |
| `test_agent_handles_port_conflict` | Error on occupied port | Same port twice |
| `test_agent_without_registry` | Works without registration | No registry_url |
| `test_agent_with_invalid_registry_url` | Handles bad URL gracefully | Malformed, unreachable |

**Edge Cases to Cover:**
- Unicode agent_id in registration
- Very long agent_id (1000 chars)
- Special characters in agent_id
- Registry returns 400, 401, 403, 404, 500, 502, 503
- Registry timeout (>10s)
- Registry connection refused

### 2. Agent Communication Tests (`test_agent_communication.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_send_message_to_agent` | HTTP POST to /a2a endpoint | Empty message, huge message |
| `test_receive_response_from_agent` | Response contains agent prefix | Empty response, timeout |
| `test_conversation_id_preserved` | Same conv_id in response | Missing conv_id, UUID format |
| `test_message_metadata_preserved` | from_agent, to_agent in metadata | Missing metadata fields |
| `test_concurrent_messages` | Multiple simultaneous requests | 10, 50, 100 concurrent |
| `test_large_message_body` | 1MB message handled | 1KB, 10KB, 100KB, 1MB |
| `test_unicode_message_content` | 12 languages preserved | Chinese, Arabic, Hebrew, etc. |

**Edge Cases to Cover:**
- Message with only whitespace
- Message with newlines, tabs
- Binary content (should reject)
- Invalid JSON body
- Missing required fields
- Wrong HTTP method (GET instead of POST)

### 3. Agent Discovery Tests (`test_agent_discovery.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_lookup_registered_agent` | GET /lookup/{id} returns agent | Case sensitivity |
| `test_lookup_unregistered_agent` | Returns 404 | Empty string, special chars |
| `test_list_all_agents` | GET /list returns all | Empty registry, 100+ agents |
| `test_search_by_capability` | Capability filter works | No matches, partial match |
| `test_agent_status_update` | PUT /status updates | Invalid status values |
| `test_agent_unregister` | DELETE removes agent | Unregister non-existent |
| `test_registry_health_check` | GET /health returns 200 | Under load |

**Edge Cases to Cover:**
- Lookup with URL-encoded special characters
- Lookup with Unicode agent_id
- Registry with 0, 1, 100, 1000 agents
- Concurrent registrations for same agent_id

### 4. @Mention Routing E2E (`test_mention_routing_e2e.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_at_mention_routes_to_target` | @agent-b message reaches agent-b | Agent not in registry |
| `test_at_mention_response_returns` | Response comes back to sender | Target returns error |
| `test_at_mention_with_registry_lookup` | Registry queried for URL | Registry returns stale URL |
| `test_at_mention_preserves_body` | Message body intact | Special chars, unicode |
| `test_at_mention_self_reference` | @self-id handled | Infinite loop prevention |
| `test_at_mention_chain` | A→B→C works | Chain depth limit |
| `test_at_mention_invalid_format` | Graceful error | @, @ space, @@, @123 |

**Edge Cases to Cover:**
- @mention at start, middle, end of message
- Multiple @mentions in one message
- @mention to offline agent
- @mention with timeout
- @mention with network error mid-response

### 5. Error Scenarios (`test_error_scenarios.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_target_agent_offline` | Error when agent unreachable | Connection refused vs timeout |
| `test_registry_offline` | Graceful degradation | Works without registry |
| `test_network_timeout` | Timeout handled | 1s, 5s, 30s timeouts |
| `test_malformed_request` | Returns 400 | Invalid JSON, missing fields |
| `test_internal_error` | Returns 500 | Agent logic throws exception |
| `test_rate_limiting` | Handles 429 | Retry-After header |
| `test_ssl_certificate_error` | Handles cert issues | Self-signed, expired |

**HTTP Error Codes to Test:**
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 408 Request Timeout
- 429 Too Many Requests
- 500 Internal Server Error
- 502 Bad Gateway
- 503 Service Unavailable
- 504 Gateway Timeout

### 6. Multi-Agent Chain Tests (`test_multi_agent_chains.py`)

| Test | What It Tests (REAL) | Edge Cases |
|------|---------------------|------------|
| `test_two_agent_conversation` | A↔B back and forth | 1, 5, 10 exchanges |
| `test_three_agent_chain` | A→B→C→A | Circular reference |
| `test_broadcast_to_multiple` | A→[B,C,D] | Concurrent sends |
| `test_conversation_isolation` | Different conv_ids isolated | Interleaved messages |
| `test_agent_failure_mid_chain` | Graceful handling | B dies mid A→B→C |
| `test_loop_detection` | Prevents infinite loops | A→B→A→B... |

---

## Test Quality Standards

### Naming Convention
```
test_[component]_[action]_[expected_outcome]

Examples:
- test_agent_startup_binds_to_specified_port
- test_registry_lookup_returns_404_for_unknown_agent
- test_at_mention_routes_message_to_target_agent
```

### Error Message Format
```python
assert response.status_code == 200, (
    f"Expected HTTP 200, got {response.status_code}. "
    f"Response body: {response.text[:200]}. "
    f"Cause: Agent may not have started or port conflict. "
    f"Fix: Check agent logs and ensure port {port} is available."
)
```

### Docstring Format
```python
def test_agent_sends_message_to_another_agent(self, agent_a, agent_b):
    """
    Given: Two agents running on different ports, both registered
    When: Agent A sends @agent-b message via HTTP POST
    Then: Agent B receives the message and returns response to A

    Tests REAL: HTTP communication, A2A protocol, registry lookup
    Mocks: None (pure E2E)
    """
```

---

## What We're NOT Mocking (REAL Components)

| Component | Why Real |
|-----------|----------|
| Agent HTTP server | Core functionality |
| A2A protocol messages | Must test real format |
| Registry HTTP API | Must test real discovery |
| Network communication | Must test real latency/errors |
| Process lifecycle | Must test real startup/shutdown |

## What We ARE Mocking (External Dependencies)

| Component | Why Mock |
|-----------|----------|
| Anthropic Claude API | External paid service |
| External MCP servers | Can't control availability |
| Smithery API | External service |

---

## Implementation Priority

### Phase 1: Core Infrastructure
1. E2E `conftest.py` with process management
2. Basic registry server fixture
3. Agent process fixture with health wait

### Phase 2: Agent Lifecycle (8 tests)
1. Startup, shutdown, registration tests
2. Port handling, error scenarios

### Phase 3: Agent Communication (12 tests)
1. Basic send/receive
2. Concurrent messages
3. Large/unicode messages

### Phase 4: Discovery & Routing (10 tests)
1. Registry operations
2. @mention routing

### Phase 5: Error & Edge Cases (15 tests)
1. Network errors
2. HTTP error codes
3. Timeout handling

### Phase 6: Multi-Agent Chains (8 tests)
1. Conversation chains
2. Loop detection

---

## Estimated Test Count

| Category | Tests | Priority |
|----------|-------|----------|
| Agent Lifecycle | 12 | P1 |
| Agent Communication | 15 | P1 |
| Agent Discovery | 12 | P2 |
| @Mention Routing | 14 | P2 |
| Error Scenarios | 18 | P2 |
| Multi-Agent Chains | 10 | P3 |
| **Total** | **81** | |

---

## Success Criteria

1. **All tests use REAL HTTP** - No mock HTTP libraries
2. **Process management works** - Agents start/stop cleanly
3. **Comprehensive edge cases** - Unicode, errors, timeouts
4. **Developer friendly** - Clear errors, easy debugging
5. **CI compatible** - No Docker required for core tests
6. **<30s total runtime** - Fast feedback

---

## Infrastructure Requirements

### Need to Create: Simple Agent Registry Server

No agent registry server exists in codebase. Must create `tests/e2e/registry_server.py`:

```python
"""
Simple in-memory agent registry for E2E testing.
Flask-based, no database dependency.
"""
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
agents = {}  # In-memory storage

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    agent_id = data.get('agent_id')
    agent_url = data.get('agent_url')
    if not agent_id or not agent_url:
        return jsonify({"error": "Missing agent_id or agent_url"}), 400
    agents[agent_id] = {
        "agent_id": agent_id,
        "agent_url": agent_url,
        "registered_at": datetime.now().isoformat()
    }
    return jsonify({"status": "registered"})

@app.route('/lookup/<agent_id>', methods=['GET'])
def lookup(agent_id):
    agent = agents.get(agent_id)
    if agent:
        return jsonify(agent)
    return jsonify({"error": "Agent not found"}), 404

@app.route('/list', methods=['GET'])
def list_agents():
    return jsonify({"agents": list(agents.values())})

@app.route('/unregister/<agent_id>', methods=['DELETE'])
def unregister(agent_id):
    if agent_id in agents:
        del agents[agent_id]
        return jsonify({"status": "unregistered"})
    return jsonify({"error": "Agent not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Decisions (User Confirmed)

1. **Registry Testing**: Test against BOTH local registry AND real `registry.chat39.com`
2. **CI Timeout**: 30 seconds max per test
3. **MCP Integration**: Include in E2E files as additional test cases, structured separately within same files

---

## Updated Test File Structure (with MCP)

```
tests/e2e/
├── conftest.py                    # E2E fixtures (process management, timeouts)
├── registry_server.py             # Simple Flask registry for local testing
├── test_agent_lifecycle.py        # Agent startup, registration, shutdown
│   └── TestMCPAgentLifecycle      # MCP-enabled agent lifecycle
├── test_agent_communication.py    # A2A message flow between agents
│   └── TestMCPCommunication       # #mcp: message routing
├── test_agent_discovery.py        # Registry lookup and discovery
│   └── TestMCPServerDiscovery     # MCP server discovery via registry
├── test_mention_routing_e2e.py    # @mention routing end-to-end
├── test_error_scenarios.py        # Network errors, timeouts, invalid agents
│   └── TestMCPErrorScenarios      # MCP-specific errors
└── test_multi_agent_chains.py     # A → B → C message chains
```

### MCP Test Cases to Add

| File | MCP Test Class | Tests |
|------|---------------|-------|
| `test_agent_communication.py` | `TestMCPCommunication` | #nanda:server, #smithery:server routing |
| `test_agent_discovery.py` | `TestMCPServerDiscovery` | MCP server lookup, list, config |
| `test_error_scenarios.py` | `TestMCPErrorScenarios` | MCP server unavailable, invalid server |

---

## Timeout Configuration

```python
# conftest.py
E2E_TIMEOUT = 30  # seconds - CI max timeout per test
PROCESS_STARTUP_TIMEOUT = 10  # seconds - wait for process to start
HTTP_REQUEST_TIMEOUT = 5  # seconds - individual HTTP request timeout
```
