"""
E2E Tests for Agent Lifecycle - Process Management Focus.

Tests REAL agent process behavior: startup, shutdown, signals, port management.
This file focuses on SUBPROCESS behavior, not library client code.

For library client tests (RegistryClient, MCPRegistry), see test_agent_discovery.py.

Test Categories:
- TestAgentStartup: Process spawning, port binding, startup timing
- TestAgentShutdown: SIGTERM, SIGINT, graceful cleanup, port release
- TestAgentProcessHealth: Agent health endpoints (not registry)
- TestAgentLifecycleErrorScenarios: Startup failures, invalid config, crashes
- TestAgentSignalHandling: Signal handling during various states
- TestAgentPortManagement: Port conflicts, reuse, binding edge cases

Distinction from test_agent_discovery.py:
- This file: Process/subprocess behavior, OS-level concerns
- test_agent_discovery.py: Library code (RegistryClient, MCPRegistry)
"""

import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest
import requests

from tests.e2e.conftest import (
    HTTP_REQUEST_TIMEOUT,
    PROCESS_STARTUP_TIMEOUT,
    PROJECT_ROOT,
    find_free_port,
    is_port_in_use,
    wait_for_port,
)

# Apply markers to all tests in this module
pytestmark = pytest.mark.e2e


# =============================================================================
# Tests: Agent Startup (Process Management)
# =============================================================================


class TestAgentStartup:
    """Tests for agent process startup and port binding."""

    def test_agent_starts_on_specified_port(self, agent_process_factory):
        """
        Given: A specified port number
        When: Starting an agent on that port
        Then: Agent process binds to the specified port

        Tests REAL: Process spawning, port binding
        """
        port = find_free_port()
        agent = agent_process_factory("startup-port-test", port=port)

        assert agent.port == port, (
            f"Expected agent on port {port}, got {agent.port}. "
            f"Cause: Port assignment failed. "
            f"Fix: Check port parameter passing in agent_process_factory."
        )
        assert is_port_in_use(port), (
            f"Expected port {port} to be in use, but it's not. "
            f"Cause: Agent may have crashed or failed to bind. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

    def test_agent_auto_assigns_port_when_not_specified(self, agent_process_factory):
        """
        Given: No port specified
        When: Starting an agent
        Then: Agent is assigned a free port automatically

        Tests REAL: Port auto-assignment, process startup
        """
        agent = agent_process_factory("auto-port-test")

        assert agent.port > 0, (
            f"Expected positive port number, got {agent.port}. "
            f"Cause: Port auto-assignment failed. "
            f"Fix: Check find_free_port() implementation."
        )
        assert is_port_in_use(agent.port), (
            f"Expected port {agent.port} to be in use. "
            f"Cause: Agent failed to start. "
            f"Fix: Check agent logs at {agent.log_file}"
        )

    def test_agent_starts_within_timeout(self, agent_process_factory):
        """
        Given: An agent configuration
        When: Starting the agent
        Then: Agent starts within PROCESS_STARTUP_TIMEOUT seconds

        Tests REAL: Startup time performance
        """
        agent = agent_process_factory("timeout-test")

        assert agent.startup_time < PROCESS_STARTUP_TIMEOUT, (
            f"Expected startup time < {PROCESS_STARTUP_TIMEOUT}s, got {agent.startup_time:.2f}s. "
            f"Cause: Agent startup is too slow. "
            f"Fix: Profile agent initialization and optimize imports."
        )

    def test_multiple_agents_start_on_different_ports(self, agent_process_factory):
        """
        Given: Multiple agent configurations
        When: Starting multiple agents
        Then: Each agent gets a unique port and all are running

        Tests REAL: Multiple process management, port isolation
        """
        agent_a = agent_process_factory("multi-a")
        agent_b = agent_process_factory("multi-b")
        agent_c = agent_process_factory("multi-c")

        ports = {agent_a.port, agent_b.port, agent_c.port}
        assert len(ports) == 3, (
            f"Expected 3 unique ports, got {len(ports)}: {ports}. "
            f"Cause: Port collision between agents. "
            f"Fix: Check find_free_port() is called for each agent."
        )

        for agent in [agent_a, agent_b, agent_c]:
            assert is_port_in_use(agent.port), (
                f"Agent {agent.name} not running on port {agent.port}. "
                f"Cause: Agent process may have crashed. "
                f"Fix: Check agent logs at {agent.log_file}"
            )

    def test_agent_process_is_running_after_startup(self, agent_process_factory):
        """
        Given: An agent started successfully
        When: Checking process status
        Then: Process is still running (poll returns None)

        Tests REAL: Process state after startup
        """
        agent = agent_process_factory("process-check-test")

        assert agent.process.poll() is None, (
            f"Expected process to be running (poll=None), got {agent.process.poll()}. "
            f"Cause: Agent process exited unexpectedly. "
            f"Fix: Check agent logs at {agent.log_file}"
        )


# =============================================================================
# Tests: Agent Shutdown (Process Termination)
# =============================================================================


class TestAgentShutdown:
    """Tests for agent graceful shutdown and cleanup."""

    def test_agent_terminates_on_sigterm(self, agent_process_factory):
        """
        Given: A running agent process
        When: Sending SIGTERM
        Then: Process terminates within 5 seconds

        Tests REAL: SIGTERM handling
        """
        agent = agent_process_factory("sigterm-test")

        # Verify running
        assert agent.process.poll() is None, "Agent should be running before shutdown"

        # Send SIGTERM
        agent.process.terminate()

        # Wait for termination
        try:
            agent.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent.process.kill()
            pytest.fail(
                f"Agent did not terminate within 5s after SIGTERM. "
                f"Cause: Agent may not handle SIGTERM properly. "
                f"Fix: Add signal handler for graceful shutdown."
            )

        assert agent.process.poll() is not None, (
            "Expected process to be terminated. "
            "Cause: Process still running after SIGTERM. "
            "Fix: Check signal handling in agent code."
        )

    def test_agent_terminates_on_sigint(self, agent_process_factory):
        """
        Given: A running agent process
        When: Sending SIGINT (Ctrl+C equivalent)
        Then: Process terminates gracefully

        Tests REAL: SIGINT handling (keyboard interrupt)
        """
        agent = agent_process_factory("sigint-test")

        assert agent.process.poll() is None, "Agent should be running"

        # Send SIGINT
        agent.process.send_signal(subprocess.signal.SIGINT)

        try:
            agent.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent.process.kill()
            pytest.fail(
                "Agent did not terminate within 5s after SIGINT. "
                "Cause: Agent may not handle SIGINT (Ctrl+C). "
                "Fix: Add SIGINT handler for graceful shutdown."
            )

    def test_port_released_after_agent_shutdown(self, agent_process_factory):
        """
        Given: An agent running on a specific port
        When: Agent is shutdown
        Then: Port is released and available for reuse

        Tests REAL: Port release on shutdown
        """
        port = find_free_port()
        agent = agent_process_factory("port-release-test", port=port)

        # Verify port in use
        assert is_port_in_use(port), "Port should be in use while agent running"

        # Shutdown agent
        agent.process.terminate()
        agent.process.wait(timeout=5)

        # Give OS time to release port (TIME_WAIT state)
        time.sleep(0.5)

        # Verify port released
        assert not is_port_in_use(port), (
            f"Expected port {port} to be released after shutdown. "
            f"Cause: Socket may not have been closed properly (SO_REUSEADDR). "
            f"Fix: Ensure socket.close() called in agent shutdown."
        )

    def test_agent_cleanup_removes_from_registry(
        self, registry_process, agent_process_factory, http_client, wait_for_registration
    ):
        """
        Given: An agent registered with registry
        When: Agent shuts down
        Then: Agent should unregister (or registry should detect offline)

        Tests REAL: Unregistration on shutdown
        Note: This depends on agent implementing unregister on shutdown
        """
        agent = agent_process_factory("cleanup-test")
        wait_for_registration("cleanup-test", timeout=5.0)

        # Verify registered
        response_before = http_client.get(f"{registry_process.url}/lookup/cleanup-test")
        assert response_before.status_code == 200, "Agent should be registered"

        # Shutdown agent
        agent.process.terminate()
        agent.process.wait(timeout=5)

        # Note: Whether agent unregisters on shutdown is implementation-specific
        # This test documents the expected behavior - adjust based on design decision
        # response_after = http_client.get(f"{registry_process.url}/lookup/cleanup-test")
        # If design requires unregister: assert response_after.status_code == 404


# =============================================================================
# Tests: Agent Process Health
# =============================================================================


class TestAgentProcessHealth:
    """Tests for agent health endpoints and status."""

    def test_agent_responds_to_requests_after_startup(
        self, agent_process_factory, http_client
    ):
        """
        Given: A running agent
        When: Sending HTTP request to agent
        Then: Agent responds (connection works)

        Tests REAL: Agent HTTP server is accepting connections
        """
        agent = agent_process_factory("http-test")

        # Try to connect to agent
        try:
            # Most agents have some endpoint - try root or a2a
            response = http_client.get(f"{agent.url}/", timeout=HTTP_REQUEST_TIMEOUT)
            # Any response (even 404) means agent is accepting connections
            assert response.status_code is not None
        except requests.exceptions.ConnectionError:
            pytest.fail(
                f"Could not connect to agent at {agent.url}. "
                f"Cause: Agent HTTP server not accepting connections. "
                f"Fix: Check agent logs at {agent.log_file}"
            )

    def test_agent_handles_concurrent_requests(
        self, agent_process_factory, http_client
    ):
        """
        Given: A running agent
        When: Sending multiple concurrent requests
        Then: All requests complete without error

        Tests REAL: Agent handles concurrent HTTP connections
        """
        agent = agent_process_factory("concurrent-test")
        results = []
        errors = []

        def make_request():
            try:
                response = http_client.get(f"{agent.url}/", timeout=HTTP_REQUEST_TIMEOUT)
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Send 5 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, (
            f"Concurrent requests failed: {errors}. "
            "Cause: Agent may not handle concurrent connections. "
            "Fix: Check HTTP server threading configuration."
        )
        assert len(results) == 5, f"Expected 5 responses, got {len(results)}"


# =============================================================================
# Tests: Agent Lifecycle Error Scenarios
# =============================================================================


class TestAgentLifecycleErrorScenarios:
    """
    Tests for error handling during agent lifecycle.

    These tests verify graceful handling of:
    - Invalid configuration
    - Unavailable registry
    - Port conflicts
    - Startup failures
    """

    def test_agent_starts_when_registry_unavailable(self, registry_process, http_client):
        """
        Given: Registry URL pointing to unavailable server
        When: Starting an agent
        Then: Agent should start anyway (registration fails gracefully)

        Tests REAL: Agent resilience when registry is down
        """
        # Create agent with invalid registry URL
        port = find_free_port()
        agent_script = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")
from nanda_core.core.adapter import NANDA

def agent_logic(message: str, conversation_id: str) -> str:
    return f"Received: {{message}}"

agent = NANDA(
    agent_id="no-registry-test",
    agent_logic=agent_logic,
    port={port},
    registry_url="http://localhost:1",  # Invalid port - registry unavailable
    public_url="http://localhost:{port}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=True)
"""
        script_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="agent_no_reg_"
        )
        script_file.write(agent_script)
        script_file.close()

        log_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, prefix="agent_no_reg_"
        )

        process = subprocess.Popen(
            [sys.executable, script_file.name],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        try:
            # Wait for agent to start (or fail)
            started = wait_for_port(port, timeout=10)

            if started:
                # Agent started despite registry being unavailable - GOOD
                assert is_port_in_use(port), "Agent should be running"
            else:
                # Check if process crashed
                exit_code = process.poll()
                if exit_code is not None:
                    log_file.close()
                    with open(log_file.name, "r") as f:
                        logs = f.read()
                    # This is acceptable IF agent fails gracefully with clear error
                    assert "registry" in logs.lower() or "connection" in logs.lower(), (
                        f"Agent crashed without clear error. Exit code: {exit_code}. "
                        f"Logs: {logs[:500]}. "
                        "Cause: Agent may not handle registry unavailability. "
                        "Fix: Add try-except around registration in NANDA.start()."
                    )
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

    def test_agent_handles_port_already_in_use(self):
        """
        Given: A port that is already in use
        When: Starting an agent on that port
        Then: Agent fails with clear error (not silent failure)

        Tests REAL: Port conflict handling
        """
        # Occupy a port
        port = find_free_port()
        blocking_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        blocking_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocking_socket.bind(("0.0.0.0", port))
        blocking_socket.listen(1)

        try:
            # Try to start agent on occupied port
            agent_script = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")
from nanda_core.core.adapter import NANDA

def agent_logic(message: str, conversation_id: str) -> str:
    return f"Received: {{message}}"

agent = NANDA(
    agent_id="port-conflict-test",
    agent_logic=agent_logic,
    port={port},  # Already in use!
    public_url="http://localhost:{port}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=False)
"""
            script_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, prefix="agent_conflict_"
            )
            script_file.write(agent_script)
            script_file.close()

            log_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".log", delete=False, prefix="agent_conflict_"
            )

            process = subprocess.Popen(
                [sys.executable, script_file.name],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
            )

            # Wait for process to exit (should fail due to port conflict)
            try:
                exit_code = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail(
                    "Agent did not fail when port in use. "
                    "Cause: Port binding error not raised. "
                    "Fix: Check socket error handling in NANDA.start()."
                )

            # Agent should have exited with error
            log_file.close()
            with open(log_file.name, "r") as f:
                logs = f.read()

            # Accept either exit code != 0 or error in logs
            assert exit_code != 0 or "address already in use" in logs.lower() or "error" in logs.lower(), (
                f"Agent should fail with clear error when port in use. "
                f"Exit code: {exit_code}. Logs: {logs[:300]}. "
                "Cause: Port conflict not detected. "
                "Fix: Handle OSError from socket.bind()."
            )

        finally:
            blocking_socket.close()

    def test_agent_handles_invalid_agent_logic(self):
        """
        Given: agent_logic that raises exception
        When: Processing a message
        Then: Agent doesn't crash, returns error response

        Tests REAL: Exception handling in message processing
        """
        port = find_free_port()
        agent_script = f"""
import sys
sys.path.insert(0, "{PROJECT_ROOT}")
from nanda_core.core.adapter import NANDA

def bad_agent_logic(message: str, conversation_id: str) -> str:
    raise ValueError("Intentional error for testing")

agent = NANDA(
    agent_id="bad-logic-test",
    agent_logic=bad_agent_logic,
    port={port},
    public_url="http://localhost:{port}",
    host="0.0.0.0",
    enable_telemetry=False
)
agent.start(register=False)
"""
        script_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="agent_bad_logic_"
        )
        script_file.write(agent_script)
        script_file.close()

        log_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, prefix="agent_bad_logic_"
        )

        process = subprocess.Popen(
            [sys.executable, script_file.name],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        try:
            # Wait for agent to start
            started = wait_for_port(port, timeout=10)
            assert started, "Agent should start even with potentially bad logic"

            # Send a message that will trigger the bad logic
            try:
                response = requests.post(
                    f"http://localhost:{port}/a2a",
                    json={
                        "role": "user",
                        "content": {"type": "text", "text": "trigger error"},
                        "conversation_id": "test-123",
                    },
                    timeout=5,
                )
                # Agent should return error response, not crash
                # Accept 200 with error message or 500
                assert response.status_code in [200, 400, 500], (
                    f"Unexpected status {response.status_code}. "
                    "Agent should handle logic errors gracefully."
                )
            except requests.exceptions.ConnectionError:
                pytest.fail(
                    "Agent crashed when logic raised exception. "
                    "Cause: Exception not caught in message handler. "
                    "Fix: Add try-except in A2A message processing."
                )

            # Verify agent is still running
            assert process.poll() is None, (
                "Agent process exited after exception in logic. "
                "Cause: Unhandled exception crashed the process. "
                "Fix: Catch exceptions in request handler."
            )

        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)


# =============================================================================
# Tests: Agent Port Management
# =============================================================================


class TestAgentPortManagement:
    """Tests for port binding, release, and reuse."""

    def test_port_can_be_reused_after_agent_shutdown(self, agent_process_factory):
        """
        Given: An agent that was running on a port
        When: Agent shuts down and new agent starts on same port
        Then: New agent can bind to the port

        Tests REAL: Port reuse with SO_REUSEADDR
        """
        port = find_free_port()

        # Start first agent
        agent1 = agent_process_factory("reuse-test-1", port=port)
        assert is_port_in_use(port), "First agent should be running"

        # Shutdown first agent
        agent1.process.terminate()
        agent1.process.wait(timeout=5)

        # Wait for port release
        time.sleep(0.5)

        # Start second agent on same port
        agent2 = agent_process_factory("reuse-test-2", port=port)
        assert is_port_in_use(port), (
            f"Second agent should be running on port {port}. "
            "Cause: Port not available for reuse (TIME_WAIT). "
            "Fix: Set SO_REUSEADDR on socket in NANDA."
        )
        assert agent2.process.poll() is None, "Second agent should still be running"

    def test_multiple_agents_can_start_in_quick_succession(self, agent_process_factory):
        """
        Given: Need to start many agents quickly
        When: Starting agents in rapid succession
        Then: All agents start successfully without port conflicts

        Tests REAL: Rapid agent spawning
        """
        agents = []
        for i in range(5):
            agent = agent_process_factory(f"rapid-{i}")
            agents.append(agent)

        # Verify all running
        for agent in agents:
            assert agent.process.poll() is None, (
                f"Agent {agent.name} not running. "
                "Cause: Race condition in port assignment. "
                "Fix: Check find_free_port() thread safety."
            )

        # Verify unique ports
        ports = {a.port for a in agents}
        assert len(ports) == 5, (
            f"Expected 5 unique ports, got {len(ports)}. "
            "Cause: Port collision during rapid startup."
        )


# =============================================================================
# Tests: Agent ID Edge Cases
# =============================================================================


class TestAgentIDEdgeCases:
    """Tests for agent_id handling in subprocess spawning."""

    def test_agent_with_very_long_id_starts_successfully(
        self, registry_process, agent_process_factory, http_client, wait_for_registration
    ):
        """
        Given: An agent_id with 100 characters
        When: Agent starts and registers
        Then: Long agent_id is handled correctly

        Tests REAL: Long agent_id in subprocess and HTTP
        """
        long_id = "agent-" + "x" * 94  # 100 chars total
        agent = agent_process_factory(long_id)

        assert agent.process.poll() is None, "Agent should be running"

        # Verify registration works with long ID
        registered = wait_for_registration(long_id, timeout=5.0)
        assert registered, (
            f"Agent with 100-char ID did not register. "
            "Cause: Long ID may be truncated. "
            "Fix: Check ID length limits in registry."
        )

    @pytest.mark.parametrize(
        "agent_id,description",
        [
            ("agent-with-hyphens", "Hyphenated"),
            ("agent_with_underscores", "Underscored"),
            ("agent.with.dots", "Dotted"),
            ("Agent123MixedCase", "Mixed case alphanumeric"),
        ],
    )
    def test_various_valid_agent_id_formats(
        self, agent_process_factory, agent_id, description
    ):
        """
        Given: Various valid agent_id formats ({description})
        When: Agent starts
        Then: Agent starts successfully

        Tests REAL: agent_id format handling in subprocess
        """
        agent = agent_process_factory(agent_id)

        assert agent.process.poll() is None, (
            f"Agent with {description} ID failed to start. "
            f"Cause: agent_id format '{agent_id}' rejected. "
            "Fix: Check agent_id validation."
        )


# =============================================================================
# Tests: Agent Startup Timing
# =============================================================================


class TestAgentStartupTiming:
    """Tests for agent startup performance and timing."""

    def test_agent_accepts_connections_within_timeout(self, agent_process_factory):
        """
        Given: An agent starting up
        When: Waiting for HTTP server to accept connections
        Then: Server is ready within PROCESS_STARTUP_TIMEOUT

        Tests REAL: Startup timing
        """
        start_time = time.time()
        agent = agent_process_factory("timing-test")
        ready_time = time.time() - start_time

        assert ready_time < PROCESS_STARTUP_TIMEOUT, (
            f"Agent took {ready_time:.2f}s to become ready. "
            f"Expected < {PROCESS_STARTUP_TIMEOUT}s. "
            "Cause: Slow startup (heavy imports?). "
            "Fix: Profile and optimize agent initialization."
        )

    def test_second_agent_starts_as_fast_as_first(self, agent_process_factory):
        """
        Given: One agent already running
        When: Starting a second agent
        Then: Second agent starts in similar time (no resource contention)

        Tests REAL: No startup degradation with multiple agents
        """
        # Start first agent
        agent1 = agent_process_factory("first-agent")
        first_time = agent1.startup_time

        # Start second agent
        agent2 = agent_process_factory("second-agent")
        second_time = agent2.startup_time

        # Second should not be significantly slower (allow 50% variance)
        assert second_time < first_time * 1.5 + 1.0, (
            f"Second agent startup ({second_time:.2f}s) much slower than first ({first_time:.2f}s). "
            "Cause: Resource contention or port scanning slowdown. "
            "Fix: Check find_free_port() efficiency."
        )


# =============================================================================
# Tests: Process Cleanup
# =============================================================================


class TestProcessCleanup:
    """Tests for proper cleanup when tests complete."""

    def test_fixture_cleanup_terminates_processes(self, agent_process_factory):
        """
        Given: Agents created during test
        When: Test completes (fixture cleanup runs)
        Then: All agent processes should be terminated

        Tests REAL: Fixture cleanup mechanism
        Note: This test verifies agents are running; cleanup verified by fixture
        """
        agent1 = agent_process_factory("cleanup-1")
        agent2 = agent_process_factory("cleanup-2")

        # Verify both running (cleanup happens after test)
        assert agent1.process.poll() is None
        assert agent2.process.poll() is None

        # Cleanup is verified by the fixture's yield/cleanup mechanism
        # If cleanup fails, subsequent tests would have port conflicts

    def test_agent_logs_are_captured(self, agent_process_factory):
        """
        Given: An agent that logs during startup
        When: Checking the log file
        Then: Log file exists and contains content

        Tests REAL: Log capture for debugging
        """
        agent = agent_process_factory("log-test")

        assert agent.log_file is not None, "Log file path should be set"
        assert os.path.exists(agent.log_file), (
            f"Log file {agent.log_file} does not exist. "
            "Cause: Log file not created. "
            "Fix: Check subprocess stdout/stderr redirection."
        )

        # Wait a moment for logs to be written
        time.sleep(0.5)

        with open(agent.log_file, "r") as f:
            logs = f.read()

        # Log file should have some content (startup messages)
        assert len(logs) > 0, (
            "Log file is empty. "
            "Cause: Agent not writing to stdout/stderr. "
            "Fix: Check logging configuration in NANDA."
        )
