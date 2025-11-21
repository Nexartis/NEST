#!/usr/bin/env python3
"""
Agent Interface - Standard interface for all agent types

This defines the contract that all agents must implement to work with NANDA.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import inspect


class AgentInterface(ABC):
    """
    Standard interface that all agents must implement.
    Framework adapters translate their specific agent types to this interface.
    """
    
    @abstractmethod
    def process_message(
        self, 
        message: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Process incoming message and return response (sync version).
        
        Args:
            message: The message content
            context: Context dictionary containing:
                - conversation_id: str - Unique conversation identifier
                - sender_id: str (optional) - ID of the sender agent
                - metadata: dict (optional) - Additional metadata
        
        Returns:
            Response string
        """
        pass
    
    async def process_message_async(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Process incoming message and return response (async version).
        
        Override this method if your agent supports async processing.
        Default implementation falls back to sync version.
        
        Args:
            message: The message content
            context: Context dictionary
        
        Returns:
            Response string
        """
        # Default: call sync version
        return self.process_message(message, context)
    
    def is_async(self) -> bool:
        """
        Check if this agent implements async processing.
        
        Returns:
            True if agent has overridden process_message_async
        """
        # Check if process_message_async is overridden
        return (
            inspect.iscoroutinefunction(self.process_message_async) and
            self.process_message_async.__func__ != AgentInterface.process_message_async.__func__
        )
    
    def get_capabilities(self) -> list:
        """
        Return list of agent capabilities (optional).
        Used for agent discovery and matching.
        
        Returns:
            List of capability strings
        """
        return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Return agent metadata (optional).
        Can include domain, specialization, version, etc.
        
        Returns:
            Dictionary of metadata
        """
        return {}