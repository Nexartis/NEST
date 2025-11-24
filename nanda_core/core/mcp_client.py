#!/usr/bin/env python3
"""
Streamlined MCP Client for the NANDA Adapter
Handles MCP server communication without message improvement
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
import mcp
import os

from ..llm.factory import create_llm_provider
from ..llm.base import LLMProvider
from ..llm.gemini import GeminiProvider
from ..llm.openai import OpenAIProvider

class MCPClient:
    """Streamlined MCP client without message preprocessing"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize MCP client with LLM provider.
        
        Args:
            api_key: LLM API key (auto-detects from env if None)
            provider: LLM provider name (auto-detected from key if None)
            model: Model name (uses default if None)
        """
        self.session = None
        self.exit_stack = AsyncExitStack()
        
        # Get API key from env if not provided
        if api_key is None:
            api_key = (
                os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("OPENAI_API_KEY") or
                os.getenv("GOOGLE_API_KEY")
            )
        
        if not api_key:
            raise ValueError(
                "No API key provided. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
                "or GOOGLE_API_KEY environment variable, or pass api_key parameter."
            )
        
        # Create LLM provider (auto-detects from key if provider not specified)
        self.llm = create_llm_provider(api_key, provider, model)
        
        logger = logging.getLogger(__name__)
        logger.info(f"🤖 [MCPClient] Using {type(self.llm).__name__} for MCP tool orchestration")

    async def connect_to_server(self, server_url: str, transport_type: str = "http", auth_headers: Optional[Dict[str, str]] = None) -> Optional[List[Any]]:
        """Connect to MCP server and return available tools"""
        try:
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔌 [MCPClient] Connecting to MCP server: {server_url}")
            logger.info(f"🔌 [MCPClient] Transport type: {transport_type}")
            logger.info(f"🔌 [MCPClient] Auth headers: {'Yes' if auth_headers else 'No'}")
            
            if transport_type.lower() == "sse":
                logger.info(f"🔌 [MCPClient] Using SSE transport")
                if auth_headers:
                    transport = await self.exit_stack.enter_async_context(sse_client(server_url, headers=auth_headers))
                else:
                    transport = await self.exit_stack.enter_async_context(sse_client(server_url))
                read_stream, write_stream = transport
            else:
                logger.info(f"🔌 [MCPClient] Using HTTP transport")
                if auth_headers:
                    transport = await self.exit_stack.enter_async_context(streamablehttp_client(server_url, headers=auth_headers))
                else:
                    transport = await self.exit_stack.enter_async_context(streamablehttp_client(server_url))
                read_stream, write_stream, _ = transport

            logger.info(f"🔌 [MCPClient] Creating MCP session...")
            self.session = await self.exit_stack.enter_async_context(
                mcp.ClientSession(read_stream, write_stream)
            )
            
            logger.info(f"🔌 [MCPClient] Initializing MCP session...")
            await self.session.initialize()

            logger.info(f"🔌 [MCPClient] Listing available tools...")
            tools_result = await self.session.list_tools()
            
            logger.info(f"🔌 [MCPClient] Found {len(tools_result.tools) if tools_result.tools else 0} tools")
            for tool in (tools_result.tools or []):
                logger.info(f"🔌 [MCPClient] Tool: {tool.name} - {tool.description}")
                
            return tools_result.tools
        except Exception as e:
            # Check for specific error types
            error_msg = str(e).lower()
            logger.error(f"❌ [MCPClient] Error connecting to MCP server: {e}")
            return None

    async def execute_query(self, query: str, server_url: str, transport_type: str = "http", auth_headers: Optional[Dict[str, str]] = None) -> str:
        """Execute query on MCP server with pluggable LLM"""
        try:
            logger = logging.getLogger(__name__)
            
            logger.info(f"🎯 [MCPClient] Executing query: {query}")
            logger.info(f"🎯 [MCPClient] Server URL: {server_url}")
            
            # Connect to server
            tools = await self.connect_to_server(server_url, transport_type, auth_headers)
            if not tools:
                logger.error(f"❌ [MCPClient] Failed to connect to MCP server")
                return "❌ Failed to connect to MCP server. Check server URL and authentication."

            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools]
            
            logger.info(f"🎯 [MCPClient] Available tools: {[t['name'] for t in available_tools]}")

            messages = [{"role": "user", "content": query}]
            logger.info(f"🎯 [MCPClient] Calling LLM with {len(available_tools)} tools")

            # Call LLM with tools using abstracted provider
            response = self.llm.call_with_tools(messages, available_tools)
            
            logger.info(f"🎯 [MCPClient] LLM response received")
            logger.info(f"🎯 [MCPClient] Response type: {type(response)}")
            logger.info(f"🎯 [MCPClient] Response has content: {hasattr(response, 'content')}")
            logger.info(f"🎯 [MCPClient] Response: {str(response)[:500]}")

            # Tool calling loop
            while True:
                tool_calls = self.llm.extract_tool_calls(response)
                logger.info(f"🎯 [MCPClient] Extracted {len(tool_calls)} tool calls")

                if not tool_calls:
                    break
                
                for tool_call in tool_calls:
                    logger.info(f"🔧 [MCPClient] LLM wants to use tool: {tool_call['name']}")
                    logger.info(f"🔧 [MCPClient] Tool input: {tool_call['input']}")
                    
                    # Execute tool via MCP
                    result = await self.session.call_tool(tool_call['name'], tool_call['input'])
                    logger.info(f"🔧 [MCPClient] Raw tool result: {str(result)[:300]}...")
                    
                    processed_result = self._parse_result(result)
                    logger.info(f"🔧 [MCPClient] Processed tool result: {str(processed_result)[:300]}...")

                    if isinstance(self.llm, GeminiProvider):
                        # Gemini doesn't need assistant tool call message
                        pass
                    elif isinstance(self.llm, OpenAIProvider):
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call["id"],
                                "type": "function",
                                "function": {
                                    "name": tool_call["name"],
                                    "arguments": json.dumps(tool_call["input"])
                                }
                            }]
                        })
                    else:
                        # Anthropic/OpenAI format
                        messages.append({
                            "role": "assistant",
                            "content": [{
                                "type": "tool_use",
                                "id": tool_call["id"],
                                "name": tool_call["name"],
                                "input": tool_call["input"]
                            }]
                        })
                    # Add tool result using provider-specific format
                    tool_result_msg = self.llm.format_tool_result(
                        tool_call["id"],
                        str(processed_result)
                    )
                    logger.info(f"🔧 [MCPClient] Formatted tool result message: {tool_result_msg}")
                    messages.append(tool_result_msg)
                    logger.info(f"🔧 [MCPClient] Messages before next LLM call: {len(messages)} messages")
                    logger.info(f"🔧 [MCPClient] Last 2 messages: {messages[-2:] if len(messages) >= 2 else messages}")

                
                # Call LLM again with tool results
                logger.info(f"🔧 [MCPClient] Calling LLM again with tool results...")
                response = self.llm.call_with_tools(messages, available_tools)
                logger.info(f"🔧 [MCPClient] Got response from LLM after tool result")

                # ADD THESE LINES:
                logger.info(f"🔧 [MCPClient] Response type after tool: {type(response)}")
                logger.info(f"🔧 [MCPClient] Response object: {response}")
                logger.info(f"🔧 [MCPClient] Attempting to extract tool calls...")

                try:
                    tool_calls_after = self.llm.extract_tool_calls(response)
                    logger.info(f"🔧 [MCPClient] Tool calls after: {len(tool_calls_after)}")
                except Exception as e:
                    logger.error(f"❌ [MCPClient] Error extracting tool calls after: {e}")
                    import traceback
                    traceback.print_exc()


            # Extract final text response
            logger.info(f"🎯 [MCPClient] Loop ended, extracting final text")
            try:
                final_response = self.llm.extract_text_content(response)
                logger.info(f"🎯 [MCPClient] Final response extracted: {final_response[:200] if final_response else 'None'}")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"❌ [MCPClient] Error executing MCP query: {e}")
                import traceback
                traceback.print_exc()  # ADD THIS LINE
                return f"❌ MCP error: {str(e)}"

            return self._parse_result(final_response) if final_response else "No response generated"

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"❌ [MCPClient] Error executing MCP query: {e}")
            return f"❌ MCP error: {str(e)}"

    def _parse_result(self, response: Any) -> str:
        """Parse JSON-RPC responses from MCP server and format as readable key-value pairs"""
        if isinstance(response, str):
            try:
                response_json = json.loads(response)
                if isinstance(response_json, dict):
                    # Handle MCP JSON-RPC format
                    if "result" in response_json:
                        artifacts = response_json["result"].get("artifacts", [])
                        if artifacts and len(artifacts) > 0:
                            parts = artifacts[0].get("parts", [])
                            if parts and len(parts) > 0:
                                text_content = parts[0].get("text", "")
                                return self._format_json_response(text_content)
                    
                    # Handle direct JSON data (like weather responses)
                    return self._format_json_response(response_json)
                    
            except json.JSONDecodeError:
                # Try to extract JSON from text response
                return self._extract_and_format_json(response)
        
        # Handle dict responses directly
        if isinstance(response, dict):
            return self._format_json_response(response)
            
        return str(response)

    def _format_json_response(self, data: Any) -> str:
        """Format JSON data into readable key-value pairs"""
        try:
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return data
            
            if isinstance(data, dict):
                formatted = []
                for key, value in data.items():
                    if isinstance(value, dict):
                        # Nested objects
                        formatted.append(f"📋 {key.replace('_', ' ').title()}:")
                        for sub_key, sub_value in value.items():
                            formatted.append(f"  • {sub_key.replace('_', ' ').title()}: {sub_value}")
                    elif isinstance(value, list):
                        # Arrays
                        formatted.append(f"📋 {key.replace('_', ' ').title()}:")
                        for i, item in enumerate(value[:5]):  # Limit to first 5 items
                            if isinstance(item, dict):
                                formatted.append(f"  [{i+1}]")
                                for sub_key, sub_value in item.items():
                                    formatted.append(f"    • {sub_key.replace('_', ' ').title()}: {sub_value}")
                            else:
                                formatted.append(f"  • {item}")
                        if len(value) > 5:
                            formatted.append(f"  ... and {len(value) - 5} more items")
                    else:
                        # Simple key-value
                        formatted.append(f"🔹 {key.replace('_', ' ').title()}: {value}")
                
                return "\n".join(formatted)
            
            elif isinstance(data, list):
                formatted = []
                for i, item in enumerate(data[:10]):  # Limit to first 10 items
                    if isinstance(item, dict):
                        formatted.append(f"📋 Item {i+1}:")
                        for key, value in item.items():
                            formatted.append(f"  • {key.replace('_', ' ').title()}: {value}")
                    else:
                        formatted.append(f"🔹 Item {i+1}: {item}")
                
                if len(data) > 10:
                    formatted.append(f"... and {len(data) - 10} more items")
                
                return "\n".join(formatted)
            
            else:
                return str(data)
                
        except Exception as e:
            return f"📄 Raw Response: {str(data)}"

    def _extract_and_format_json(self, text: str) -> str:
        """Extract JSON from text and format it"""
        try:
            # Look for JSON patterns in the text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    data = json.loads(json_str)
                    return self._format_json_response(data)
                except json.JSONDecodeError:
                    pass
            
            # If no JSON found, return original text
            return text
            
        except Exception:
            return text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            logger = logging.getLogger(__name__)
            logger.info(f"🔌 [MCPClient] Cleaning up MCP client...")
            
            # Clean up session first
            if self.session:
                try:
                    logger.info(f"🔌 [MCPClient] Closing MCP session...")
                    # Don't just set to None, let exit_stack handle cleanup
                    self.session = None
                except Exception as e:
                    logger.warning(f"⚠️ [MCPClient] Error closing session: {e}")
            
            # Clean up exit stack (this handles all async context managers)
            try:
                logger.info(f"🔌 [MCPClient] Closing exit stack...")
                await self.exit_stack.aclose()
                logger.info(f"✅ [MCPClient] MCP client cleanup complete")
            except Exception as e:
                logger.warning(f"⚠️ [MCPClient] Error closing exit stack: {e}")
                # Don't re-raise, just log and continue
                
        except Exception as e:
            logger.error(f"❌ [MCPClient] Unexpected error during cleanup: {e}")
            # Don't re-raise cleanup errors to avoid masking original exceptions