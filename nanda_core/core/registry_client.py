"""
Registry Client for NANDA Index Registry Integration
Handles agent registration, discovery, and management
"""

import httpx
import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for interacting with the NANDA Index registry"""

    def __init__(self, registry_url: Optional[str] = None):
        """Initialize registry client
        
        Args:
            registry_url: URL of NANDA Index (e.g., http://registry.chat39.com:6900)
        """
        self.registry_url = registry_url or self._get_default_registry_url()
        # Use async httpx client instead of requests
        self.client = httpx.AsyncClient(timeout=30.0, verify=False)  # verify=False for dev with self-signed certs
        logger.info(f"Registry client initialized with URL: {self.registry_url}")

    def _get_default_registry_url(self) -> str:
        """Get default registry URL from configuration"""
        try:
            if os.path.exists("registry_url.txt"):
                with open("registry_url.txt", "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        return "https://registry.chat39.com"

    async def register(self, agent_facts: Dict[str, Any]) -> bool:
        """Register an agent with the registry using AgentFacts
        
        Args:
            agent_facts: Agent metadata dict with fields:
                - agent_id: str
                - name: str
                - domain: str (optional)
                - specialization: str (optional)
                - description: str (optional)
                - capabilities: list
                - url: str
                - agent_url: str (backward compatibility)
                - supported_protocols: list
                - endpoints: dict
        
        Returns:
            True if registration successful, False otherwise
        """
        if not self.registry_url:
            logger.warning("No registry URL configured, skipping registration")
            return False
        
        try:
            # Support both new (register) and old (register_agent) endpoints
            response = await self.client.post(
                f"{self.registry_url}/register",
                json=agent_facts
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Agent {agent_facts.get('agent_id')} registered successfully")
                return True
            else:
                logger.error(f"❌ Registration failed: HTTP {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registering agent: {e}")
            return False

    async def register_agent(self, agent_id: str, agent_url: str, 
                            api_url: Optional[str] = None, 
                            agent_facts_url: Optional[str] = None) -> bool:
        """Legacy registration method for backward compatibility"""
        data = {
            "agent_id": agent_id,
            "agent_url": agent_url
        }
        if api_url:
            data["api_url"] = api_url
        if agent_facts_url:
            data["agent_facts_url"] = agent_facts_url
        
        try:
            response = await self.client.post(f"{self.registry_url}/register", json=data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return False

    async def resolve(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Resolve/lookup an agent in the registry
        
        Args:
            agent_id: Agent identifier to look up
            
        Returns:
            Agent info dict or None if not found
        """
        return await self.lookup_agent(agent_id)

    async def lookup_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Look up an agent in the registry"""
        if not self.registry_url:
            logger.warning("No registry URL configured")
            return None
            
        try:
            response = await self.client.get(f"{self.registry_url}/lookup/{agent_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Agent {agent_id} not found: HTTP {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error looking up agent {agent_id}: {e}")
            return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        if not self.registry_url:
            return []
            
        try:
            response = await self.client.get(f"{self.registry_url}/list")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return []

    async def list_clients(self) -> List[Dict[str, Any]]:
        """List all registered clients"""
        if not self.registry_url:
            return []
            
        try:
            response = await self.client.get(f"{self.registry_url}/clients")
            if response.status_code == 200:
                return response.json()
            return await self.list_agents()  # Fallback to list endpoint
        except Exception as e:
            logger.error(f"Error listing clients: {e}")
            return []

    async def get_agent_metadata(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for an agent"""
        agent_info = await self.lookup_agent(agent_id)
        if not agent_info:
            return None

        # Extract additional metadata if available
        metadata = {
            "agent_id": agent_id,
            "agent_url": agent_info.get("agent_url"),
            "url": agent_info.get("url"),
            "api_url": agent_info.get("api_url"),
            "endpoints": agent_info.get("endpoints", {}), 
            "supported_protocols": agent_info.get("supported_protocols", ["a2a"]), 
            "last_seen": agent_info.get("last_seen"),
            "capabilities": agent_info.get("capabilities", []),
            "description": agent_info.get("description", ""),
            "tags": agent_info.get("tags", []),
            "domain": agent_info.get("domain"),  
            "specialization": agent_info.get("specialization") 
        }
        
        return metadata

    async def search_agents(self, query: str = "", capabilities: List[str] = None, 
                           tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search for agents based on criteria"""
        if not self.registry_url:
            return []
            
        try:
            params = {}
            if query:
                params["q"] = query
            if capabilities:
                params["capabilities"] = ",".join(capabilities)
            if tags:
                params["tags"] = ",".join(tags)

            response = await self.client.get(f"{self.registry_url}/search", params=params)
            if response.status_code == 200:
                return response.json()

            # Fallback to client-side filtering
            return await self._filter_agents_locally(query, capabilities, tags)
        except Exception as e:
            logger.error(f"Error searching agents: {e}")
            return await self._filter_agents_locally(query, capabilities, tags)

    async def _filter_agents_locally(self, query: str = "", capabilities: List[str] = None, 
                                     tags: List[str] = None) -> List[Dict[str, Any]]:
        """Fallback local filtering when server search is not available"""
        all_agents = await self.list_agents()
        filtered = []

        for agent in all_agents:
            # Simple text matching for query
            if query:
                agent_text = f"{agent.get('agent_id', '')} {agent.get('description', '')}"
                if query.lower() not in agent_text.lower():
                    continue

            # Capability matching
            if capabilities:
                agent_caps = agent.get('capabilities', [])
                if not any(cap in agent_caps for cap in capabilities):
                    continue

            # Tag matching
            if tags:
                agent_tags = agent.get('tags', [])
                if not any(tag in agent_tags for tag in tags):
                    continue

            filtered.append(agent)

        return filtered

    async def get_mcp_servers(self, registry_provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available MCP servers"""
        if not self.registry_url:
            return []
            
        try:
            params = {}
            if registry_provider:
                params["registry_provider"] = registry_provider

            response = await self.client.get(f"{self.registry_url}/mcp_servers", params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting MCP servers: {e}")
            return []

    async def get_mcp_server_config(self, registry_provider: str, 
                                   qualified_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific MCP server"""
        if not self.registry_url:
            return None
            
        try:
            response = await self.client.get(f"{self.registry_url}/get_mcp_registry", params={
                'registry_provider': registry_provider,
                'qualified_name': qualified_name
            })

            if response.status_code == 200:
                result = response.json()
                config = result.get("config")
                config_json = json.loads(config) if isinstance(config, str) else config

                return {
                    "endpoint": result.get("endpoint"),
                    "config": config_json,
                    "registry_provider": result.get("registry_provider")
                }
            return None
        except Exception as e:
            logger.error(f"Error getting MCP server config: {e}")
            return None

    async def update_agent_status(self, agent_id: str, status: str, 
                                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update agent status and metadata"""
        if not self.registry_url:
            return False
            
        try:
            data = {
                "agent_id": agent_id,
                "status": status,
                "last_seen": datetime.now().isoformat()
            }
            if metadata:
                data.update(metadata)

            response = await self.client.put(
                f"{self.registry_url}/agents/{agent_id}/status", 
                json=data
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry"""
        if not self.registry_url:
            return False
            
        try:
            response = await self.client.delete(f"{self.registry_url}/agents/{agent_id}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error unregistering agent: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if the registry is healthy"""
        if not self.registry_url:
            return False
            
        try:
            response = await self.client.get(f"{self.registry_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    async def get_registry_stats(self) -> Optional[Dict[str, Any]]:
        """Get registry statistics"""
        if not self.registry_url:
            return None
            
        try:
            response = await self.client.get(f"{self.registry_url}/stats")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting registry stats: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()