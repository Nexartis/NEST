#!/usr/bin/env python3
"""
OpenAI LLM Provider for MCP tool calling
"""

from typing import List, Dict, Any
from .base import LLMProvider

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider for MCP tool orchestration"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: GPT model name
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Install with: pip install openai")
        
        super().__init__(api_key, model)
        self.client = OpenAI(api_key=api_key)
    
    def call_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        max_tokens: int = 1024
    ) -> Any:
        """Call GPT with tools"""
        # Convert MCP tool format to OpenAI function format
        openai_tools = self._convert_tools_to_openai(tools)
        
        return self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            tools=openai_tools,
            tool_choice="auto"
        )
    
    def _convert_tools_to_openai(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool format to OpenAI function format"""
        openai_tools = []
        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        return openai_tools
    
    def extract_text_content(self, response: Any) -> str:
        """Extract text from GPT response"""
        message = response.choices[0].message
        if message.content:
            return message.content
        return ""
    
    def extract_tool_calls(self, response: Any) -> List[Dict[str, Any]]:
        """Extract tool calls from GPT response"""
        message = response.choices[0].message
        tool_calls = []
        
        if message.tool_calls:
            for tc in message.tool_calls:
                import json
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": json.loads(tc.function.arguments)
                })
        
        return tool_calls
    
    def format_tool_result(self, tool_call_id: str, result: str) -> Dict[str, Any]:
        """Format tool result for GPT"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(result)
        }