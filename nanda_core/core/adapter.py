"""
Simple NANDA Adapter - Clean Agent-to-Agent Communication

Simple, clean adapter focused on A2A communication without complexity.
8-10 lines to deploy an agent.
"""

import os
import asyncio
import requests
from typing import Optional, Callable
from .agent_bridge import AgentBridge
from .registry_client import RegistryClient
from ..protocols.router import ProtocolRouter
from ..protocols.a2a.protocol import A2AProtocol


class NANDA:
    """Simple NANDA class for clean agent deployment"""
    
    def __init__(self, 
                 agent_id: str,
                 agent_logic: Callable[[str, str], str],
                 agent_name: Optional[str] = None,
                 domain: Optional[str] = None,
                 specialization: Optional[str] = None,
                 description: Optional[str] = None,
                 capabilities: Optional[list] = None,
                 port: int = 6000,
                 registry_url: Optional[str] = None,
                 public_url: Optional[str] = None,
                 host: str = "0.0.0.0",
                 enable_telemetry: bool = True,
                 protocols: Optional[dict] = None):
        """
        Create a simple NANDA agent
        
        Args:
            agent_id: Unique agent identifier
            agent_logic: Function that takes (message: str, conversation_id: str) -> response: str
            agent_name: Display name (defaults to agent_id)
            domain: Agent's domain of expertise
            specialization: Agent's specialization
            description: Agent description
            capabilities: List of capabilities (default: ["text"])
            port: Port to run on
            registry_url: Optional registry URL for agent discovery
            public_url: Public URL for agent registration (e.g., https://yourdomain.com:6000)
            host: Host to bind to
            enable_telemetry: Enable telemetry logging
            protocols: Dict of protocol configs (e.g., {"a2a": {"enabled": True}})
        """
        self.agent_id = agent_id
        self.agent_logic = agent_logic
        self.agent_name = agent_name or agent_id
        self.domain = domain
        self.specialization = specialization
        self.description = description or f"AI agent {agent_id}"
        self.capabilities = capabilities or ["text"]
        self.port = port
        self.registry_url = registry_url
        self.public_url = public_url or f"http://localhost:{port}"
        self.host = host
        self.enable_telemetry = enable_telemetry
        self.protocols_config = protocols or {"a2a": {"enabled": True}}
        
        # Initialize telemetry if enabled
        self.telemetry = None
        if enable_telemetry:
            try:
                from ..telemetry.telemetry_system import TelemetrySystem
                self.telemetry = TelemetrySystem(agent_id)
                print(f"📊 Telemetry enabled for {agent_id}")
            except ImportError:
                print(f"⚠️ Telemetry requested but module not available")
        
        # Initialize protocol router
        self.router = ProtocolRouter()
        
        # Initialize and register protocols
        self._initialize_protocols()
        
        # Initialize registry client
        self.registry = RegistryClient(registry_url) if registry_url else RegistryClient(None)
        
        # Create the bridge
        self.bridge = AgentBridge(
            protocol_router=self.router,
            registry_client=self.registry,
            agent_id=agent_id,
            agent_logic=agent_logic,
            telemetry=self.telemetry
        )
        
        print(f"🤖 NANDA Agent '{agent_id}' created")
        if registry_url:
            print(f"🌐 Registry: {registry_url}")
        print(f"🔗 Public URL: {self.public_url}")
        print(f"🔌 Protocols: {self.router.get_all_protocols()}")
    
    def _initialize_protocols(self):
        """Initialize and register protocol adapters based on config"""
        
        # Initialize A2A protocol if enabled
        if self.protocols_config.get("a2a", {}).get("enabled", True):
            a2a_protocol = A2AProtocol(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                public_url=self.public_url,
                domain=self.domain,
                specialization=self.specialization,
                description=self.description,
                capabilities=self.capabilities
            )
            self.router.register(a2a_protocol)
        
        # TODO: Add SLIM protocol when implemented
        # if self.protocols_config.get("slim", {}).get("enabled"):
        #     slim_protocol = SLIMProtocol(...)
        #     self.router.register(slim_protocol)
    
    async def start(self, register: bool = True):
        """Start the agent server"""
        # Register with registry if provided
        if register and self.registry_url:
            await self._register()
        
        print(f"🚀 Starting agent '{self.agent_id}' on {self.host}:{self.port}")
        
        # Start the bridge (which starts all protocol servers)
        await self.bridge.run_server(self.host, self.port)
    
    async def _register(self):
        """Register agent with NANDA Index"""
        try:
            agent_facts = {
                "agent_id": self.agent_id,
                "name": self.agent_name,
                "domain": self.domain,
                "specialization": self.specialization,
                "description": self.description,
                "capabilities": self.capabilities,
                "url": self.public_url,
                "agent_url": self.public_url,  # For backward compatibility
                "supported_protocols": self.router.get_all_protocols(),
                "endpoints": self._get_endpoints()
            }
            
            await self.registry.register(agent_facts)
            print(f"✅ Agent '{self.agent_id}' registered successfully")
            
        except Exception as e:
            print(f"⚠️ Registration error: {e}")
    
    def _get_endpoints(self) -> dict:
        """Get endpoints for all registered protocols
        
        Returns:
            Dict mapping protocol names to endpoint URLs
        """
        endpoints = {}
        for protocol_name in self.router.get_all_protocols():
            if protocol_name == "a2a":
                endpoints["a2a"] = f"{self.public_url}/a2a"
            elif protocol_name == "slim":
                endpoints["slim"] = f"grpc://{self.public_url}:50051"
        
        return endpoints
    
    def stop(self):
        """Stop the agent and cleanup resources"""
        # Cleanup protocol resources
        try:
            try:
                # Try to get the currently running event loop
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, schedule the cleanup
                asyncio.create_task(self.router.cleanup_all())
            except RuntimeError:
                # No event loop running, create one and run cleanup
                asyncio.run(self.router.cleanup_all())
        except Exception as e:
            print(f"⚠️  Error during protocol cleanup: {e}")

        # Cleanup telemetry
        if self.telemetry:
            self.telemetry.stop()

        print(f"🛑 Stopping agent '{self.agent_id}'")