#!/usr/bin/env python3
"""
Streamlined MCP Client for the NANDA Adapter
Handles MCP server discovery and communication without message improvement
"""

import json
import base64
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
import mcp
from anthropic import Anthropic
import os


class MCPClient:
    """Streamlined MCP client without message preprocessing"""

    def __init__(self):
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    async def connect_to_server(self, server_url: str, transport_type: str = "http") -> Optional[List[Any]]:
        """Connect to MCP server and return available tools"""
        try:
            if transport_type.lower() == "sse":
                transport = await self.exit_stack.enter_async_context(sse_client(server_url))
                read_stream, write_stream = transport
            else:
                transport = await self.exit_stack.enter_async_context(streamablehttp_client(server_url))
                read_stream, write_stream, _ = transport

            self.session = await self.exit_stack.enter_async_context(
                mcp.ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()

            tools_result = await self.session.list_tools()
            return tools_result.tools
        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            return None

    async def execute_query(self, query: str, server_url: str, transport_type: str = "http") -> str:
        """Execute query on MCP server without message improvement"""
        try:
            tools = await self.connect_to_server(server_url, transport_type)
            if not tools:
                return "Failed to connect to MCP server"

            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools]

            messages = [{"role": "user", "content": query}]

            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=messages,
                tools=available_tools
            )

            while True:
                has_tool_calls = False

                for block in message.content:
                    if block.type == "tool_use":
                        has_tool_calls = True
                        result = await self.session.call_tool(block.name, block.input)
                        processed_result = self._parse_result(result)

                        messages.append({
                            "role": "assistant",
                            "content": [{
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            }]
                        })

                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(processed_result)
                            }]
                        })

                if not has_tool_calls:
                    break

                message = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    messages=messages,
                    tools=available_tools
                )

            final_response = ""
            for block in message.content:
                if block.type == "text":
                    final_response += block.text + "\n"

            return self._parse_result(final_response.strip()) if final_response else "No response generated"

        except Exception as e:
            return f"Error: {str(e)}"

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
        await self.exit_stack.aclose()
        self.session = None


class MCPRegistry:
    """Handles MCP server discovery from the registry"""

    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.smithery_api_key = os.getenv("SMITHERY_API_KEY", "")

    def get_server_config(self, registry_provider: str, qualified_name: str) -> Optional[Dict[str, Any]]:
        """Query registry for MCP server configuration"""
        try:
            import requests

            response = requests.get(f"{self.registry_url}/get_mcp_registry", params={
                'registry_provider': registry_provider,
                'qualified_name': qualified_name
            })

            if response.status_code == 200:
                result = response.json()
                endpoint = result.get("endpoint")
                config = result.get("config")
                config_json = json.loads(config) if isinstance(config, str) else config
                registry_name = result.get("registry_provider")

                return {
                    "endpoint": endpoint,
                    "config": config_json,
                    "registry_provider": registry_name
                }
            return None

        except Exception as e:
            print(f"Error querying MCP registry: {e}")
            return None

    def build_server_url(self, endpoint: str, config: Dict[str, Any], registry_provider: str) -> Optional[str]:
        """Build the final MCP server URL with authentication"""
        try:
            if registry_provider == "smithery":
                if not self.smithery_api_key:
                    print("SMITHERY_API_KEY not found in environment")
                    return None

                config_b64 = base64.b64encode(json.dumps(config).encode()).decode()
                return f"{endpoint}?api_key={self.smithery_api_key}&config={config_b64}"
            else:
                return endpoint
        except Exception as e:
            print(f"Error building server URL: {e}")
            return None

    def lookup_nanda_mcp_server(self, server_name: str) -> Optional[str]:
        """Look up NANDA MCP server URL from MongoDB registry"""
        try:
            import requests
            
            # Query NANDA MCP registry endpoint
            response = requests.get(
                f"{self.registry_url}/mcp_servers/{server_name}", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                server_url = data.get("server_url") or data.get("endpoint")
                print(f"Found NANDA MCP server {server_name}: {server_url}")
                return server_url
            else:
                print(f"NANDA MCP server {server_name} not found (status: {response.status_code})")
                return None
                
        except Exception as e:
            print(f"Error looking up NANDA MCP server {server_name}: {e}")
            return None

    def execute_mcp_query_sync(self, server_url: str, query: str) -> str:
        """Execute MCP query synchronously"""
        try:
            # Run async MCP query in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                async def run_query():
                    async with MCPClient() as client:
                        return await client.execute_query(query, server_url)
                
                result = loop.run_until_complete(run_query())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            print(f"Error executing MCP query: {e}")
            return f"Error executing MCP query: {str(e)}"

    def handle_nanda_mcp_query(self, server_name: str, query: str) -> str:
        """Handle NANDA MCP registry queries"""
        try:
            # Query NANDA MCP registry (MongoDB collection)
            server_url = self.lookup_nanda_mcp_server(server_name)
            if not server_url:
                return f"❌ MCP server '{server_name}' not found in NANDA registry"
            
            # Execute MCP query
            result = self.execute_mcp_query_sync(server_url, query)
            return f"🔧 NANDA MCP [{server_name}]: {result}"
            
        except Exception as e:
            return f"❌ Error querying NANDA MCP server: {str(e)}"

    def handle_smithery_mcp_query(self, server_name: str, query: str) -> str:
        """Handle Smithery MCP registry queries"""
        try:
            if not self.smithery_api_key:
                return "❌ SMITHERY_API_KEY not found in environment variables"
            
            # Query Smithery registry via NANDA registry service
            server_config = self.get_server_config("smithery", server_name)
            
            if not server_config:
                return f"❌ Smithery MCP server '{server_name}' not found"
            
            # Build server URL with authentication
            server_url = self.build_server_url(
                server_config["endpoint"], 
                server_config["config"], 
                "smithery"
            )
            
            if not server_url:
                return f"❌ Failed to build Smithery MCP server URL for '{server_name}'"
            
            # Execute MCP query
            result = self.execute_mcp_query_sync(server_url, query)
            return f"🔧 Smithery MCP [{server_name}]: {result}"
            
        except Exception as e:
            return f"❌ Error querying Smithery MCP server: {str(e)}"