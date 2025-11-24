#!/usr/bin/env python3
"""
Telemetry System - Pluggable telemetry with multiple backends
"""

from typing import Dict, Any, List, Optional
from .backend import TelemetryBackend
from .console_backend import ConsoleBackend


class TelemetrySystem:
    """
    Telemetry system with pluggable backends.
    Default: Console output with 50-line buffer.
    """
    
    def __init__(
        self,
        agent_id: str,
        backends: Optional[List[TelemetryBackend]] = None
    ):
        """
        Initialize telemetry system.
        
        Args:
            agent_id: Agent identifier
            backends: List of telemetry backends (defaults to ConsoleBackend)
        """
        self.agent_id = agent_id
        
        # Default to console backend if none provided
        if backends is None:
            self.backends = [ConsoleBackend(buffer_size=50, enabled=True)]
        else:
            self.backends = backends
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log event to all backends.
        
        Args:
            event_type: Type of event
            data: Event data
        """
        for backend in self.backends:
            try:
                backend.log_event(self.agent_id, event_type, data)
            except Exception as e:
                print(f"⚠️ Telemetry backend error: {e}")
    
    # Convenience methods for common events
    def log_message_received(self, conversation_id: str, message: str = ""):
        """Log incoming message"""
        self.log_event('message_received', {
            'conversation_id': conversation_id,
            'message': message
        })
    
    def log_message_sent(self, target_agent: str, conversation_id: str):
        """Log outgoing message to another agent"""
        self.log_event('message_sent', {
            'target_agent': target_agent,
            'conversation_id': conversation_id
        })
    
    def log_error(self, error: str, context: Optional[Dict] = None):
        """Log error"""
        self.log_event('error', {
            'error': error,
            'context': context or {}
        })
    
    def log_mcp_call(self, server: str, query: str):
        """Log MCP server call"""
        self.log_event('mcp_call', {
            'server': server,
            'query': query
        })
    
    def log_agent_started(self, port: int):
        """Log agent startup"""
        self.log_event('agent_started', {
            'port': port
        })
    
    def get_recent_logs(self, n: int = 50) -> list:
        """
        Get recent logs from first backend that supports it.
        
        Args:
            n: Number of logs to retrieve
            
        Returns:
            List of log entries
        """
        for backend in self.backends:
            if hasattr(backend, 'get_recent_logs'):
                return backend.get_recent_logs(n)
        return []
    
    def stop(self):
        """Stop and cleanup all backends"""
        for backend in self.backends:
            try:
                backend.close()
            except Exception as e:
                print(f"⚠️ Error closing telemetry backend: {e}")