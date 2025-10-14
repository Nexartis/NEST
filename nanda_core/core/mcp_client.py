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
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔌 [MCPClient] Connecting to MCP server: {server_url}")
            logger.info(f"🔌 [MCPClient] Transport type: {transport_type}")
            
            if transport_type.lower() == "sse":
                logger.info(f"🔌 [MCPClient] Using SSE transport")
                transport = await self.exit_stack.enter_async_context(sse_client(server_url))
                read_stream, write_stream = transport
            else:
                logger.info(f"🔌 [MCPClient] Using HTTP transport")
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
            logger.error(f"❌ [MCPClient] Error connecting to MCP server: {e}")
            return None

    async def execute_query(self, query: str, server_url: str, transport_type: str = "http") -> str:
        """Execute query on MCP server without message improvement"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🎯 [MCPClient] Executing query: {query}")
            logger.info(f"🎯 [MCPClient] Server URL: {server_url}")
            
            tools = await self.connect_to_server(server_url, transport_type)
            if not tools:
                logger.error(f"❌ [MCPClient] Failed to connect to MCP server")
                return "Failed to connect to MCP server"

            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools]
            
            logger.info(f"🎯 [MCPClient] Available tools for Claude: {[t['name'] for t in available_tools]}")

            messages = [{"role": "user", "content": query}]
            logger.info(f"🎯 [MCPClient] Sending query to Claude with {len(available_tools)} tools")

            message = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=messages,
                tools=available_tools
            )
            
            logger.info(f"🎯 [MCPClient] Claude response received with {len(message.content)} content blocks")

            while True:
                has_tool_calls = False

                for block in message.content:
                    if block.type == "tool_use":
                        has_tool_calls = True
                        logger.info(f"🔧 [MCPClient] Claude wants to use tool: {block.name}")
                        logger.info(f"🔧 [MCPClient] Tool input: {block.input}")
                        
                        result = await self.session.call_tool(block.name, block.input)
                        logger.info(f"🔧 [MCPClient] Raw tool result: {str(result)[:300]}...")
                        
                        processed_result = self._parse_result(result)
                        logger.info(f"🔧 [MCPClient] Processed tool result: {str(processed_result)[:300]}...")

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
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔌 [MCPClient] Cleaning up MCP client...")
            
            if self.session:
                logger.info(f"🔌 [MCPClient] Closing MCP session...")
                # Don't explicitly close session, let exit_stack handle it
                self.session = None
            
            logger.info(f"🔌 [MCPClient] Closing exit stack...")
            await self.exit_stack.aclose()
            logger.info(f"✅ [MCPClient] MCP client cleanup complete")
            
        except Exception as e:
            logger.error(f"❌ [MCPClient] Error during cleanup: {e}")


class MCPRegistry:
    """Handles MCP server discovery from the registry"""

    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.smithery_api_key = os.getenv("SMITHERY_API_KEY", "")

    def get_server_config(self, registry_provider: str, qualified_name: str) -> Optional[Dict[str, Any]]:
        """Query registry for MCP server configuration"""
        try:
            import requests
            import logging
            logger = logging.getLogger(__name__)

            query_url = f"{self.registry_url}/get_mcp_registry"
            params = {
                'registry_provider': registry_provider,
                'qualified_name': qualified_name
            }
            
            logger.info(f"🌐 [MCPRegistry] Querying registry: {query_url} with params: {params}")
            
            response = requests.get(query_url, params=params)
            
            logger.info(f"🌐 [MCPRegistry] Registry response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🌐 [MCPRegistry] Registry response data: {result}")
                
                endpoint = result.get("endpoint")
                config = result.get("config")
                config_json = json.loads(config) if isinstance(config, str) else config
                registry_name = result.get("registry_provider")

                server_config = {
                    "endpoint": endpoint,
                    "config": config_json,
                    "registry_provider": registry_name
                }
                
                logger.info(f"🌐 [MCPRegistry] Parsed server config: {server_config}")
                return server_config
            else:
                logger.warning(f"🌐 [MCPRegistry] Registry query failed with status {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ [MCPRegistry] Error querying MCP registry: {e}")
            return None

    def build_server_url(self, endpoint: str, config: Dict[str, Any], registry_provider: str) -> Optional[str]:
        """Build the final MCP server URL with authentication"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🔧 [MCPRegistry] Building server URL for {registry_provider}")
            logger.info(f"🔧 [MCPRegistry] Endpoint: {endpoint}")
            logger.info(f"🔧 [MCPRegistry] Config: {config}")
            
            if registry_provider == "smithery":
                if not self.smithery_api_key:
                    logger.error(f"❌ [MCPRegistry] SMITHERY_API_KEY not found in environment")
                    return None

                logger.info(f"🔧 [MCPRegistry] Using Smithery API key: {self.smithery_api_key[:10]}...")
                
                config_b64 = base64.b64encode(json.dumps(config).encode()).decode()
                logger.info(f"🔧 [MCPRegistry] Config base64 encoded: {config_b64[:50]}...")
                
                final_url = f"{endpoint}?api_key={self.smithery_api_key}&config={config_b64}"
                logger.info(f"🔧 [MCPRegistry] Final Smithery URL: {final_url[:100]}...")
                
                return final_url
            else:
                logger.info(f"🔧 [MCPRegistry] Using direct endpoint for {registry_provider}: {endpoint}")
                return endpoint
        except Exception as e:
            logger.error(f"❌ [MCPRegistry] Error building server URL: {e}")
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
        """Execute MCP query synchronously using asyncio.run"""
        try:
            import logging
            import asyncio
            logger = logging.getLogger(__name__)
            
            logger.info(f"🚀 [MCPRegistry] Executing MCP query: {query}")
            logger.info(f"🚀 [MCPRegistry] Server URL: {server_url}")
            
            async def run_query():
                async with MCPClient() as client:
                    return await client.execute_query(query, server_url)
            
            # Run the async function in a new event loop
            result = asyncio.run(run_query())
            logger.info(f"✅ [MCPRegistry] MCP query completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ [MCPRegistry] Error executing MCP query: {e}")
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

    def get_smithery_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server information directly from Smithery registry"""
        try:
            import requests
            import logging
            logger = logging.getLogger(__name__)
            
            if not self.smithery_api_key:
                logger.error(f"❌ [SmitheryAPI] SMITHERY_API_KEY not found")
                return None
            
            # Use Smithery's direct API
            smithery_url = f"https://registry.smithery.ai/servers/{server_id}"
            headers = {
                "Authorization": f"Bearer {self.smithery_api_key}"
            }
            
            logger.info(f"🏭 [SmitheryAPI] Querying Smithery registry: {smithery_url}")
            logger.info(f"🏭 [SmitheryAPI] Using API key: {self.smithery_api_key[:10]}...")
            
            response = requests.get(smithery_url, headers=headers, timeout=10)
            logger.info(f"🏭 [SmitheryAPI] Smithery response status: {response.status_code}")
            
            if response.status_code == 200:
                server_info = response.json()
                logger.info(f"🏭 [SmitheryAPI] Smithery server info: {server_info}")
                return server_info
            else:
                logger.error(f"❌ [SmitheryAPI] Failed to get server info: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ [SmitheryAPI] Error querying Smithery API: {e}")
            return None

    def build_smithery_server_url(self, server_info: Dict[str, Any]) -> Optional[str]:
        """Build Smithery MCP server URL from server info"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Extract deployment URL and config from Smithery response
            deployment_url = server_info.get("deploymentUrl")
            connections = server_info.get("connections", [])
            
            logger.info(f"🔧 [SmitheryURL] Deployment URL: {deployment_url}")
            logger.info(f"🔧 [SmitheryURL] Connections: {connections}")
            
            if not deployment_url:
                logger.error(f"❌ [SmitheryURL] No deployment URL found in server info")
                return None
            
            # Find the stdio connection (typical for MCP)
            stdio_connection = None
            for conn in connections:
                if conn.get("type") == "stdio":
                    stdio_connection = conn
                    break
            
            if not stdio_connection:
                logger.warning(f"⚠️ [SmitheryURL] No stdio connection found, using deployment URL directly")
                return deployment_url
            
            # Build URL with config if available
            config_schema = stdio_connection.get("configSchema", {})
            logger.info(f"🔧 [SmitheryURL] Config schema: {config_schema}")
            
            # For now, use the deployment URL directly
            # In future, we might need to handle config encoding
            final_url = deployment_url
            logger.info(f"🔧 [SmitheryURL] Final URL: {final_url}")
            
            return final_url
            
        except Exception as e:
            logger.error(f"❌ [SmitheryURL] Error building Smithery URL: {e}")
            return None

    def handle_smithery_mcp_query(self, server_name: str, query: str) -> str:
        """Handle Smithery MCP registry queries using direct Smithery API"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"🏭 [SmitheryMCP] Starting Smithery MCP query for server: {server_name}")
            logger.info(f"🏭 [SmitheryMCP] Query: {query}")
            
            if not self.smithery_api_key:
                logger.error(f"❌ [SmitheryMCP] SMITHERY_API_KEY not found in environment variables")
                return "❌ SMITHERY_API_KEY not found in environment variables"
            
            # Get server info from Smithery registry
            logger.info(f"🏭 [SmitheryMCP] Getting server info from Smithery registry...")
            server_info = self.get_smithery_server_info(server_name)
            
            if not server_info:
                logger.error(f"❌ [SmitheryMCP] Smithery MCP server '{server_name}' not found")
                return f"❌ Smithery MCP server '{server_name}' not found in Smithery registry"
            
            # Build server URL
            logger.info(f"🏭 [SmitheryMCP] Building MCP server URL...")
            server_url = self.build_smithery_server_url(server_info)
            
            if not server_url:
                logger.error(f"❌ [SmitheryMCP] Failed to build server URL for '{server_name}'")
                return f"❌ Failed to build MCP server URL for '{server_name}'"
            
            logger.info(f"🏭 [SmitheryMCP] Built server URL: {server_url}")
            
            # Execute MCP query
            logger.info(f"🏭 [SmitheryMCP] Executing MCP query...")
            result = self.execute_mcp_query_sync(server_url, query)
            
            logger.info(f"🏭 [SmitheryMCP] Query completed, result length: {len(str(result))}")
            return f"🔧 Smithery MCP [{server_name}]: {result}"
            
        except Exception as e:
            logger.error(f"❌ [SmitheryMCP] Error querying Smithery MCP server: {e}", exc_info=True)
            return f"❌ Error querying Smithery MCP server: {str(e)}"