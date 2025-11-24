#!/usr/bin/env python3
"""
Simple NANDA Adapter - Clean Agent-to-Agent Communication

Simple, clean adapter focused on A2A communication without complexity.
8-10 lines to deploy an agent.
"""

import os
import requests
from typing import Optional, Callable, Union
from python_a2a import run_server
from .agent_bridge import SimpleAgentBridge

# Import AgentInterface and adapters
from ..interface import AgentInterface
from ..adapters import SimpleAdapter


class NANDA:
    """Simple NANDA class for clean agent deployment"""
    
    def __init__(self, 
                 agent_id: str,
                 agent_logic: Optional[Callable[[str, str], str]] = None,
                 agent: Optional[AgentInterface] = None,
                 port: int = 6000,
                 registry_url: Optional[str] = None,
                 mcp_registry_url: Optional[str] = None,
                 public_url: Optional[str] = None,
                 host: str = "0.0.0.0",
                 enable_telemetry: bool = True,
                 smithery_api_key: Optional[str] = None):
        """
        Create a simple NANDA agent
        
        Args:
            agent_id: Unique agent identifier
            agent_logic: [DEPRECATED] Function that takes (message: str, conversation_id: str) -> response: str
            agent: AgentInterface implementation (new way - supports any framework)
            port: Port to run on
            registry_url: Optional registry URL for agent discovery
            mcp_registry_url: Optional MCP registry URL for MCP server discovery
            public_url: Public URL for agent registration (e.g., https://yourdomain.com:6000)
            host: Host to bind to
            enable_telemetry: Enable telemetry logging (optional)
            smithery_api_key: Optional Smithery API key for MCP server authentication
        """
        self.agent_id = agent_id
        self.port = port
        self.registry_url = registry_url
        self.mcp_registry_url = mcp_registry_url
        self.public_url = public_url
        self.host = host
        self.enable_telemetry = enable_telemetry
        self.smithery_api_key = smithery_api_key
        
        # Handle both old (agent_logic) and new (agent) interfaces
        if agent is not None and agent_logic is not None:
            raise ValueError("Cannot specify both 'agent' and 'agent_logic'. Use 'agent' for new code.")
        
        if agent is not None:
            # New way: user provided AgentInterface
            self.agent = agent
            print(f"🔧 Using AgentInterface: {type(agent).__name__}")
        elif agent_logic is not None:
            # Old way: wrap simple function with SimpleAdapter for backward compatibility
            self.agent = SimpleAdapter(agent_logic)
            print(f"🔧 Using SimpleAdapter (backward compatibility mode)")
        else:
            raise ValueError("Must specify either 'agent' (AgentInterface) or 'agent_logic' (function)")
        
        # Initialize telemetry if enabled
        self.telemetry = None
        self.log_server = None
        if enable_telemetry:
            try:
                from ..telemetry.telemetry_system import TelemetrySystem
                from ..telemetry.log_server import LogStreamServer
                
                self.telemetry = TelemetrySystem(agent_id)
                
                # Start log streaming server on port+1
                self.log_server = LogStreamServer(
                    telemetry_system=self.telemetry,
                    port=port + 1
                )
                self.log_server.start()
                
                print(f"📊 Telemetry enabled for {agent_id}")
                print(f"📡 Logs: http://localhost:{port + 1}/logs")
            except ImportError:
                print(f"⚠️ Telemetry requested but module not available")
        
        # Create the bridge with the agent
        self.bridge = SimpleAgentBridge(
            agent_id=agent_id,
            agent=self.agent,
            registry_url=registry_url,
            telemetry=self.telemetry,
            mcp_registry_url=mcp_registry_url,
            smithery_api_key=smithery_api_key
        )
        
        print(f"🤖 NANDA Agent '{agent_id}' created")
        if registry_url:
            print(f"🌐 Registry: {registry_url}")
        if public_url:
            print(f"🔗 Public URL: {public_url}")
    
    def start(self, register: bool = True):
        """Start the agent server"""
        # Register with registry if provided
        if register and self.registry_url and self.public_url:
            self._register()
        
        print(f"🚀 Starting agent '{self.agent_id}' on {self.host}:{self.port}")
        
        # Start the A2A server
        run_server(self.bridge, host=self.host, port=self.port)
    
    def _register(self):
        """Register agent with registry"""
        try:
            data = {
                "agent_id": self.agent_id,
                "agent_url": self.public_url
            }
            response = requests.post(f"{self.registry_url}/register", json=data, timeout=10)
            if response.status_code == 200:
                print(f"✅ Agent '{self.agent_id}' registered successfully")
            else:
                print(f"⚠️ Failed to register agent: HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️ Registration error: {e}")
    
    def stop(self):
        """Stop the agent and cleanup telemetry"""
        if self.telemetry:
            self.telemetry.stop()
        print(f"🛑 Stopping agent '{self.agent_id}'")