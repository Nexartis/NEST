# NEST Tests

Comprehensive test suite for NEST framework.

## Structure

```
tests/
├── README.md                           # This file
├── __init__.py                        # Package marker
└── test_protocols/                    # Protocol tests
    ├── __init__.py
    └── test_a2a_protocol.py          # A2A protocol tests (PR #12)
```

## Running Tests

### Install pytest

```bash
pip install pytest pytest-asyncio
```

### Run all tests

```bash
pytest tests/ -v
```

### Run specific test file

```bash
pytest tests/test_protocols/test_a2a_protocol.py -v
```

### Run specific test class

```bash
pytest tests/test_protocols/test_a2a_protocol.py::TestResourceCleanup -v
```

### Run with coverage

```bash
pip install pytest-cov
pytest tests/ --cov=nanda_core --cov-report=html
```

## Test Categories

### 1. Backward Compatibility Tests (`TestA2AProtocolBackwardCompatibility`)

Tests that ensure the new implementation doesn't break existing functionality:
- NANDA initialization with default A2A protocol
- Protocol router integration
- Agent bridge integration

### 2. Official A2A Protocol Tests (`TestOfficialA2AProtocol`)

Tests for the new official A2A protocol implementation:
- Protocol initialization
- HTTP client creation
- AgentCard generation
- Metadata formatting
- Message handler setup

### 3. Resource Cleanup Tests (`TestResourceCleanup`)

Tests for PR #12 resource cleanup fixes:
- A2A protocol cleanup closes HTTP client
- ProtocolRouter cleanup_all() works correctly
- NANDA.stop() triggers cleanup properly
- Error handling during cleanup

### 4. Integration Tests (`TestIntegration`)

End-to-end tests for complete workflows:
- Full agent lifecycle (create -> use -> stop)

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pip install pytest pytest-asyncio
    pytest tests/ -v
```

## Adding New Tests

1. Create test file in appropriate subdirectory
2. Follow naming convention: `test_*.py`
3. Use descriptive test names: `test_feature_does_something`
4. Add docstrings explaining what's being tested
5. Update this README if adding new test categories
