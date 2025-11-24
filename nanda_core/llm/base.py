#!/usr/bin/env python3
"""
Base LLM Provider interface for MCP tool calling
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMProvider(ABC):
    """
    Base interface for LLM providers.
    Used by MCP client for tool orchestration.
    """
    
    def __init__(self, api_key: str, model: str):
        """
        Initialize LLM provider.
        
        Args:
            api_key: API key for the provider
            model: Model name
        """
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 1024
    ) -> Any:
        """
        Call LLM with tool definitions.
        
        Args:
            messages: Conversation messages in format [{"role": "user", "content": "..."}]
            tools: Tool definitions in MCP format
            max_tokens: Maximum tokens for response
        
        Returns:
            Provider-specific response object
        """
        pass
    
    @abstractmethod
    def extract_text_content(self, response: Any) -> str:
        """
        Extract text content from LLM response.
        
        Args:
            response: Provider-specific response object
        
        Returns:
            Text content as string
        """
        pass
    
    @abstractmethod
    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response.
        
        Args:
            response: Provider-specific response object
        
        Returns:
            List of tool calls: [{"id": "...", "name": "...", "input": {...}}]
        """
        pass
    
    @abstractmethod
    def format_tool_result(self, tool_call_id: str, result: str) -> Dict[str, Any]:
        """
        Format tool result for next LLM call.
        
        Args:
            tool_call_id: ID of the tool call
            result: Tool execution result
        
        Returns:
            Formatted message for LLM
        """
        pass