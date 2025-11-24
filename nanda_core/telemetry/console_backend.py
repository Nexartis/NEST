#!/usr/bin/env python3
"""
Console Telemetry Backend - Pretty formatted terminal output
"""

from typing import Dict, Any
from datetime import datetime
from collections import deque
from .backend import TelemetryBackend


class ConsoleBackend(TelemetryBackend):
    """
    Console backend with colored output and circular buffer.
    Stores last N logs for retrieval.
    """
    
    def __init__(self, buffer_size: int = 50, enabled: bool = True):
        """
        Args:
            buffer_size: Number of recent logs to keep
            enabled: Whether to print to console
        """
        self.buffer_size = buffer_size
        self.enabled = enabled
        self.logs = deque(maxlen=buffer_size)
        
        # ANSI color codes
        self.COLORS = {
            'reset': '\033[0m',
            'green': '\033[92m',
            'blue': '\033[94m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'cyan': '\033[96m',
            'magenta': '\033[95m'
        }
    
    def log_event(self, agent_id: str, event_type: str, data: Dict[str, Any]):
        """Log event to console and buffer"""
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        log_entry = {
            'timestamp': timestamp,
            'agent_id': agent_id,
            'event_type': event_type,
            'data': data
        }
        
        # Add to buffer
        self.logs.append(log_entry)
        
        # Print to console if enabled
        if self.enabled:
            self._print_formatted(log_entry)
    
    def _print_formatted(self, entry: Dict[str, Any]):
        """Pretty print log entry"""
        event_type = entry['event_type']
        agent_id = entry['agent_id']
        data = entry['data']
        
        # Choose color and icon based on event type
        if event_type == 'message_received':
            icon = '📨'
            color = self.COLORS['blue']
            msg = f"Received: {data.get('message', '')[:50]}"
        elif event_type == 'message_sent':
            icon = '📤'
            color = self.COLORS['green']
            msg = f"Sent to {data.get('target_agent', 'unknown')}"
        elif event_type == 'error':
            icon = '❌'
            color = self.COLORS['red']
            msg = f"Error: {data.get('error', '')[:50]}"
        elif event_type == 'mcp_call':
            icon = '🔧'
            color = self.COLORS['magenta']
            msg = f"MCP: {data.get('server', '')} - {data.get('query', '')[:30]}"
        elif event_type == 'agent_started':
            icon = '🚀'
            color = self.COLORS['cyan']
            msg = f"Agent started on port {data.get('port', '')}"
        else:
            icon = '📝'
            color = self.COLORS['reset']
            msg = str(data)
        
        # Format output
        print(f"{color}{icon} [{agent_id}] {msg}{self.COLORS['reset']}")
    
    def get_recent_logs(self, n: int = 50) -> list:
        """Get last N log entries"""
        return list(self.logs)[-n:]
    
    def close(self):
        """Cleanup"""
        self.logs.clear()