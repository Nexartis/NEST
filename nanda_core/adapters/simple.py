#!/usr/bin/env python3
"""
Simple Adapter - Wraps simple (str, str) -> str functions

This adapter provides backward compatibility with existing NANDA agents
that use simple callable functions.
"""

from typing import Callable, Dict, Any
from ..interface import AgentInterface


class SimpleAdapter(AgentInterface):
    """
    Adapter for simple agent logic functions.
    
    Wraps functions with signature: (message: str, conversation_id: str) -> str
    """
    
    def __init__(self, agent_logic: Callable[[str, str], str]):
        """
        Initialize adapter with agent logic function.
        
        Args:
            agent_logic: Function taking (message, conversation_id) returning response
        """
        self.agent_logic = agent_logic
    
    def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Process message using the wrapped agent logic function.
        
        Args:
            message: The message content
            context: Context dict with conversation_id
        
        Returns:
            Response from agent logic
        """
        conversation_id = context.get("conversation_id", "default")
        return self.agent_logic(message, conversation_id)
    
    def get_capabilities(self) -> list:
        """Simple adapters don't define capabilities."""
        return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """Simple adapters don't define metadata."""
        return {}