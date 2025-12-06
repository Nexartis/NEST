"""
E2E Test Fixtures for NEST.

Provides process management fixtures for running REAL agent and registry
processes during E2E testing. Unlike unit/integration fixtures that use mocks,
these fixtures start actual HTTP servers and test real network communication.

Key Fixtures:
- registry_process: Starts a real registry server
- agent_process_factory: Factory to spawn real agent processes
- http_client: Configured requests session with timeouts
- real_registry_url: URL to real registry.chat39.com for production tests

Timeout Configuration:
- E2E_TIMEOUT: 30s max per test (CI limit)
- PROCESS_STARTUP_TIMEOUT: 10s to wait for process startup
- HTTP_REQUEST_TIMEOUT: 5s per HTTP request
"""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# Timeout Configuration
# =============================================================================

E2E_TIMEOUT = 30  # seconds - CI max timeout per test
PROCESS_STARTUP_TIMEOUT = 10  # seconds - wait for process to start
HTTP_REQUEST_TIMEOUT = 5  # seconds - individual HTTP request timeout
HEALTH_CHECK_INTERVAL = 0.2  # seconds - interval between health checks


# =============================================================================
# Pytest Markers
# =============================================================================

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(E2E_TIMEOUT)]


# =============================================================================
# Path Configuration
# =============================================================================

# Get project root (NEST directory)
E2E_DIR = Path(__file__).parent
TESTS_DIR = E2E_DIR.parent
PROJECT_ROOT = TESTS_DIR.parent
NANDA_CORE_DIR = PROJECT_ROOT / "nanda_core"

# Add project to path for imports
sys.path.insert(0, str(PROJECT_ROOT))

# Import real library code for E2E testing
from nanda_core.core.registry_client import RegistryClient
from nanda_core.core.mcp_registry import MCPRegistry


# =============================================================================
# Process Management Dataclass
# =============================================================================


@dataclass
class ProcessInfo:
    """Information about a running process."""

    process: subprocess.Popen
    port: int
    url: str
    name: str
    log_file: Optional[str] = None
    startup_time: float = 0.0


@dataclass
class ProcessManager:
    """Manages multiple processes for E2E tests."""

    processes: List[ProcessInfo] = field(default_factory=list)

    def add(self, info: ProcessInfo) -> None:
        """Add a process to track."""
        self.processes.append(info)

    def cleanup(self) -> None:
        """Kill all tracked processes."""
        for info in reversed(self.processes):
            try:
                if info.process.poll() is None:
                    info.process.terminate()
                    try:
                        info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        info.process.kill()
                        info.process.wait()
            except Exception:
                pass
        self.processes.clear()


# =============================================================================
# Port Management
# =============================================================================


def find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


# =============================================================================
# Health Check Utilities
# =============================================================================


def wait_for_http(url: str, timeout: float = PROCESS_STARTUP_TIMEOUT) -> bool:
    """
    Wait for an HTTP endpoint to become available.

    Args:
        url: URL to check (e.g., http://localhost:5000/health)
        timeout: Maximum time to wait in seconds

    Returns:
        True if endpoint is available, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code < 500:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(HEALTH_CHECK_INTERVAL)
    return False


def wait_for_port(port: int, timeout: float = PROCESS_STARTUP_TIMEOUT) -> bool:
    """
    Wait for a port to become available.

    Args:
        port: Port number to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if port is listening, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(HEALTH_CHECK_INTERVAL)
    return False


def wait_for_condition(
    condition_fn: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = HEALTH_CHECK_INTERVAL,
    description: str = "condition",
) -> bool:
    """
    Wait for a condition to become true (replaces time.sleep).

    Args:
        condition_fn: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        description: Description for error messages

    Returns:
        True if condition met, False if timeout

    Example:
        # Instead of: time.sleep(0.5)
        # Use: wait_for_condition(lambda: agent_registered(agent_id), description="agent registration")
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            if condition_fn():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def wait_for_agent_registered(
    registry_url: str, agent_id: str, timeout: float = 5.0
) -> bool:
    """
    Wait for an agent to appear in the registry.

    Args:
        registry_url: URL of the registry server
        agent_id: Agent ID to look for
        timeout: Maximum time to wait in seconds

    Returns:
        True if agent found, False if timeout
    """

    def check_registered():
        try:
            response = requests.get(f"{registry_url}/lookup/{agent_id}", timeout=1)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    return wait_for_condition(
        check_registered,
        timeout=timeout,
        description=f"agent '{agent_id}' registration",
    )


# =============================================================================
# Debug Helpers
# =============================================================================


def get_agent_logs(agent_info: "ProcessInfo", tail_lines: int = 50) -> str:
    """
    Get the last N lines from an agent's log file.

    Args:
        agent_info: ProcessInfo object for the agent
        tail_lines: Number of lines to return

    Returns:
        Last N lines of the log file
    """
    if not agent_info.log_file:
        return "(no log file)"
    try:
        with open(agent_info.log_file, "r") as f:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
    except Exception as e:
        return f"(error reading logs: {e})"


def format_assertion_error(
    expected: Any,
    got: Any,
    cause: str,
    fix: str,
    agent_info: Optional["ProcessInfo"] = None,
) -> str:
    """
    Format a detailed assertion error message.

    Args:
        expected: What was expected
        got: What was actually received
        cause: Probable cause of the failure
        fix: Suggested fix
        agent_info: Optional agent ProcessInfo for log context

    Returns:
        Formatted error message string
    """
    msg = f"Expected: {expected}. " f"Got: {got}. " f"Cause: {cause}. " f"Fix: {fix}."
    if agent_info:
        msg += f"\nAgent logs:\n{get_agent_logs(agent_info, tail_lines=20)}"
    return msg


# =============================================================================
# HTTP Client Fixture
# =============================================================================


@pytest.fixture
def http_client() -> requests.Session:
    """
    Create a requests session with retry and timeout configuration.

    Configured for E2E testing with:
    - 3 retries on connection errors
    - 5 second timeout per request
    - Exponential backoff
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default timeout
    session.request = lambda method, url, **kwargs: requests.Session.request(
        session,
        method,
        url,
        timeout=kwargs.pop("timeout", HTTP_REQUEST_TIMEOUT),
        **kwargs,
    )

    return session


# =============================================================================
# Registry Server Fixture
# =============================================================================


@pytest.fixture(scope="module")
def registry_process() -> Generator[ProcessInfo, None, None]:
    """
    Start a real registry server process.

    Starts the E2E test registry server on a free port and waits for it
    to become healthy. Automatically cleans up on fixture teardown.

    Yields:
        ProcessInfo with process handle, port, and URL

    Example:
        def test_registry(registry_process):
            response = requests.get(f"{registry_process.url}/health")
            assert response.status_code == 200
    """
    port = find_free_port()
    registry_script = E2E_DIR / "registry_server.py"

    log_file = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)

    process = subprocess.Popen(
        [sys.executable, str(registry_script), "--port", str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
    )

    url = f"http://localhost:{port}"
    start_time = time.time()

    # Wait for registry to be ready
    if not wait_for_http(f"{url}/health"):
        process.kill()
        log_file.close()
        with open(log_file.name, "r") as f:
            logs = f.read()
        pytest.fail(
            f"Registry server failed to start on port {port} within {PROCESS_STARTUP_TIMEOUT}s. "
            f"Logs: {logs[:500]}"
        )

    startup_time = time.time() - start_time

    info = ProcessInfo(
        process=process,
        port=port,
        url=url,
        name="registry",
        log_file=log_file.name,
        startup_time=startup_time,
    )

    yield info

    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    log_file.close()


# =============================================================================
# Agent Process Factory Fixture
# =============================================================================


@pytest.fixture
def agent_process_factory(registry_process) -> Generator[Callable, None, None]:
    """
    Factory fixture to spawn real agent processes.

    Creates a factory function that can spawn multiple agents on different
    ports. All agents are automatically cleaned up on fixture teardown.

    Yields:
        Function(agent_id, port=None, registry_url=None) -> ProcessInfo

    Example:
        def test_two_agents(agent_process_factory):
            agent_a = agent_process_factory("agent-a")
            agent_b = agent_process_factory("agent-b")
            # Both agents are now running and registered
    """
    manager = ProcessManager()

    def create_agent(
        agent_id: str,
        port: Optional[int] = None,
        registry_url: Optional[str] = None,
        public_url: Optional[str] = None,
    ) -> ProcessInfo:
        """
        Spawn a real agent process.

        Args:
            agent_id: Unique identifier for the agent
            port: Port to run on (auto-assigned if None)
            registry_url: Registry URL (uses test registry if None)
            public_url: Public URL for registration (auto-generated if None)

        Returns:
            ProcessInfo with process handle, port, and URL
        """
        if port is None:
            port = find_free_port()

        if registry_url is None:
            registry_url = registry_process.url

        if public_url is None:
            public_url = f"http://localhost:{port}"

        # Create a simple agent script
        agent_script = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")
from nanda_core.core.adapter import NANDA

def agent_logic(message: str, conversation_id: str) -> str:
    return f"[{agent_id}] Received: {{message}}"

agent = NANDA(
    agent_id="{agent_id}",
    agent_logic=agent_logic,
    port={port},
    registry_url="{registry_url}",
    public_url="{public_url}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=True)
"""

        # Write to temp file
        script_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix=f"agent_{agent_id}_"
        )
        script_file.write(agent_script)
        script_file.close()

        log_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, prefix=f"agent_{agent_id}_"
        )

        process = subprocess.Popen(
            [sys.executable, script_file.name],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        url = f"http://localhost:{port}"
        start_time = time.time()

        # Wait for agent to be ready (check A2A endpoint)
        # The A2A server may not have a /health endpoint, so we check the port
        if not wait_for_port(port):
            process.kill()
            log_file.close()
            with open(log_file.name, "r") as f:
                logs = f.read()
            pytest.fail(
                f"Agent '{agent_id}' failed to start on port {port} within {PROCESS_STARTUP_TIMEOUT}s. "
                f"Cause: Process may have crashed or port binding failed. "
                f"Fix: Check agent logs: {logs[:500]}"
            )

        # Wait for agent to register with registry (replaces time.sleep(0.5) in tests)
        # This ensures agent is fully ready before returning
        if not wait_for_agent_registered(registry_url, agent_id, timeout=5.0):
            # Registration may fail but agent is still running - that's OK
            # Log warning but don't fail (some tests test unregistered agents)
            pass

        startup_time = time.time() - start_time

        info = ProcessInfo(
            process=process,
            port=port,
            url=url,
            name=agent_id,
            log_file=log_file.name,
            startup_time=startup_time,
        )

        manager.add(info)
        return info

    yield create_agent

    # Cleanup all spawned agents
    manager.cleanup()


# =============================================================================
# Real Registry URL Fixture
# =============================================================================


@pytest.fixture
def real_registry_url() -> str:
    """
    URL to the real NANDA registry for production tests.

    Returns:
        https://registry.chat39.com
    """
    return "https://registry.chat39.com"


@pytest.fixture
def registry_client(registry_process) -> RegistryClient:
    """
    Create a real RegistryClient pointing to the test registry.

    This tests the ACTUAL RegistryClient class from nanda_core,
    not just raw HTTP requests.

    Example:
        def test_with_real_client(registry_client):
            result = registry_client.register_agent("test", "http://localhost:5000")
            assert result is True
    """
    return RegistryClient(registry_url=registry_process.url)


@pytest.fixture
def mcp_registry(registry_process) -> MCPRegistry:
    """
    Create a real MCPRegistry pointing to the test registry.

    This tests the ACTUAL MCPRegistry class from nanda_core.

    Example:
        def test_with_real_mcp_registry(mcp_registry, mcp_test_server):
            info = mcp_registry.get_nanda_mcp_server_info("test-server")
    """
    return MCPRegistry(
        mcp_registry_url=registry_process.url,
        agent_registry_url=registry_process.url,
    )


@pytest.fixture
def real_registry_available(real_registry_url: str) -> bool:
    """
    Check if the real registry is available.

    Use this to skip tests that require the real registry when offline.

    Example:
        def test_real_registry(real_registry_available, real_registry_url):
            if not real_registry_available:
                pytest.skip("Real registry not available")
    """
    try:
        response = requests.get(f"{real_registry_url}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_agent_data() -> Dict[str, Any]:
    """Sample agent registration data."""
    return {
        "agent_id": "test-agent",
        "agent_url": "http://localhost:6000",
        "name": "Test Agent",
        "description": "A test agent for E2E testing",
        "capabilities": ["test", "echo"],
        "tags": ["e2e", "test"],
    }


@pytest.fixture
def sample_mcp_server_data() -> Dict[str, Any]:
    """Sample MCP server registration data."""
    return {
        "qualified_name": "test-mcp-server",
        "endpoint": "http://localhost:7000/mcp",
        "description": "Test MCP server",
        "provider": "nanda",
    }


@pytest.fixture(scope="module")
def mcp_test_server() -> Generator[ProcessInfo, None, None]:
    """
    Start a real MCP test server for testing MCP integration.

    Starts the MCP test server on a free port and waits for it
    to become healthy. Automatically cleans up on fixture teardown.

    Yields:
        ProcessInfo with process handle, port, and URL
    """
    port = find_free_port()
    mcp_script = E2E_DIR / "mcp_test_server.py"

    log_file = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)

    process = subprocess.Popen(
        [sys.executable, str(mcp_script), "--port", str(port)],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
    )

    url = f"http://localhost:{port}"
    start_time = time.time()

    # Wait for MCP server to be ready
    if not wait_for_http(f"{url}/health"):
        process.kill()
        log_file.close()
        with open(log_file.name, "r") as f:
            logs = f.read()
        pytest.fail(
            f"MCP test server failed to start on port {port} within {PROCESS_STARTUP_TIMEOUT}s. "
            f"Logs: {logs[:500]}"
        )

    startup_time = time.time() - start_time

    info = ProcessInfo(
        process=process,
        port=port,
        url=url,
        name="mcp-test-server",
        log_file=log_file.name,
        startup_time=startup_time,
    )

    yield info

    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    log_file.close()


@pytest.fixture
def mcp_enabled_agent_factory(
    registry_process, mcp_test_server
) -> Generator[Callable, None, None]:
    """
    Factory to create agents with MCP registry configured.

    Creates agents that can make real MCP queries to the test MCP server.
    """
    manager = ProcessManager()

    def create_mcp_agent(agent_id: str) -> ProcessInfo:
        port = find_free_port()

        agent_script = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")
from nanda_core.core.adapter import NANDA

def agent_logic(message: str, conversation_id: str) -> str:
    return f"[{agent_id}] Received: {{message}}"

agent = NANDA(
    agent_id="{agent_id}",
    agent_logic=agent_logic,
    port={port},
    registry_url="{registry_process.url}",
    mcp_registry_url="{registry_process.url}",
    public_url="http://localhost:{port}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=True)
"""

        script_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix=f"mcp_agent_{agent_id}_"
        )
        script_file.write(agent_script)
        script_file.close()

        log_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, prefix=f"mcp_agent_{agent_id}_"
        )

        process = subprocess.Popen(
            [sys.executable, script_file.name],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        url = f"http://localhost:{port}"

        if not wait_for_port(port):
            process.kill()
            log_file.close()
            with open(log_file.name, "r") as f:
                logs = f.read()
            pytest.fail(f"MCP Agent '{agent_id}' failed to start: {logs[:500]}")

        info = ProcessInfo(
            process=process,
            port=port,
            url=url,
            name=agent_id,
            log_file=log_file.name,
        )

        manager.add(info)
        return info

    yield create_mcp_agent

    manager.cleanup()


# =============================================================================
# Unicode Test Data Fixtures
# =============================================================================


@pytest.fixture
def unicode_agent_ids() -> List[Tuple[str, str]]:
    """
    Unicode agent IDs for internationalization testing.

    Returns list of (agent_id, description) tuples covering 12 languages.
    """
    return [
        ("代理", "Chinese characters"),
        ("エージェント", "Japanese characters"),
        ("агент", "Cyrillic characters"),
        ("에이전트", "Korean Hangul"),
        ("وكيل", "Arabic RTL script"),
        ("סוכן", "Hebrew RTL script"),
        ("ตัวแทน", "Thai script"),
        ("एजेंट", "Hindi Devanagari"),
        ("café-agent", "French accents"),
        ("αβγ-agent", "Greek letters"),
        ("🤖-bot", "Emoji"),
        ("agent،test", "Arabic comma punctuation"),
    ]


@pytest.fixture
def unicode_messages() -> List[Tuple[str, str]]:
    """
    Unicode messages for internationalization testing.

    Returns list of (message, description) tuples.
    """
    return [
        ("你好世界", "Chinese"),
        ("こんにちは", "Japanese"),
        ("Привет мир", "Cyrillic"),
        ("안녕하세요", "Korean"),
        ("مرحبا بالعالم", "Arabic"),
        ("שלום עולם", "Hebrew"),
        ("สวัสดีโลก", "Thai"),
        ("नमस्ते दुनिया", "Hindi"),
        ("Bonjour le monde", "French"),
        ("Γεια σου κόσμε", "Greek"),
        ("Hello 🌍🎉", "Emoji"),
    ]


# =============================================================================
# Registry Reset Fixture
# =============================================================================


@pytest.fixture(autouse=True)
def reset_registry(registry_process, http_client) -> Generator[None, None, None]:
    """
    Automatically reset registry state before each test.

    This fixture runs before each test to ensure a clean registry state.
    """
    # Reset before test
    http_client.post(f"{registry_process.url}/_reset")
    yield
    # Optionally reset after test too (uncomment if needed)
    # http_client.post(f"{registry_process.url}/_reset")


# =============================================================================
# Polling Fixtures (replace time.sleep)
# =============================================================================


@pytest.fixture
def wait_for_registration(registry_process) -> Callable:
    """
    Fixture to wait for agent registration (replaces time.sleep(0.5)).

    Returns a function that waits for an agent to appear in the registry.

    Example:
        def test_agent(agent_process_factory, wait_for_registration):
            agent = agent_process_factory("my-agent")
            wait_for_registration("my-agent")  # Instead of time.sleep(0.5)
    """

    def _wait(agent_id: str, timeout: float = 5.0) -> bool:
        return wait_for_agent_registered(registry_process.url, agent_id, timeout)

    return _wait


@pytest.fixture
def wait_for_agents(registry_process) -> Callable:
    """
    Fixture to wait for multiple agents to register.

    Example:
        def test_multi_agent(agent_process_factory, wait_for_agents):
            agent_a = agent_process_factory("agent-a")
            agent_b = agent_process_factory("agent-b")
            wait_for_agents(["agent-a", "agent-b"])
    """

    def _wait(agent_ids: List[str], timeout: float = 5.0) -> bool:
        for agent_id in agent_ids:
            if not wait_for_agent_registered(registry_process.url, agent_id, timeout):
                return False
        return True

    return _wait


# =============================================================================
# A2A Message Helpers
# =============================================================================


@pytest.fixture
def send_a2a_message(http_client) -> Callable:
    """
    Helper to send A2A protocol messages to an agent.

    Returns a function that sends messages in A2A format.

    Example:
        def test_message(send_a2a_message, agent_process_factory):
            agent = agent_process_factory("test-agent")
            response = send_a2a_message(agent.url, "Hello!")
            assert "Received" in response
    """

    def _send(
        agent_url: str, message: str, conversation_id: str = None
    ) -> Dict[str, Any]:
        """Send an A2A message to an agent."""
        payload = {
            "role": "user",
            "content": {"type": "text", "text": message},
            "conversation_id": conversation_id or f"test-{time.time()}",
        }

        response = http_client.post(
            f"{agent_url}/a2a", json=payload, timeout=HTTP_REQUEST_TIMEOUT
        )

        return {
            "status_code": response.status_code,
            "response": (
                response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else response.text
            ),
            "headers": dict(response.headers),
        }

    return _send
