#!/usr/bin/env python3
"""
Anthropic LLM Provider for MCP tool calling
"""

from typing import List, Dict, Any
from .base import LLMProvider

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for MCP tool orchestration"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Claude model name
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        
        super().__init__(api_key, model)
        self.client = Anthropic(api_key=api_key)
    
    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 1024
    ) -> Any:
        """Call Claude with tools"""
        return self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools
        )
    
    def extract_text_content(self, response: Any) -> str:
        """Extract text from Claude response"""
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
        return "\n".join(text_parts)
    
    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from Claude response"""
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
        return tool_calls
    
    def format_tool_result(self, tool_call_id: str, result: str) -> Dict[str, Any]:
        """Format tool result for Claude"""
        return {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": str(result)
            }]
        }