#!/usr/bin/env python3
"""
Telemetry Backend Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class TelemetryBackend(ABC):
    """Base interface for telemetry backends"""
    
    @abstractmethod
    def log_event(
        self,
        agent_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Log a telemetry event"""
        pass
    
    @abstractmethod
    def get_recent_logs(self, n: int = 50) -> list:
        """Get last N log entries"""
        pass
    
    @abstractmethod
    def close(self):
        """Cleanup"""
        pass