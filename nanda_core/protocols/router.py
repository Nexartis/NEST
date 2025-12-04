from typing import Dict, List, Optional
from .base import AgentProtocol

class ProtocolRouter:
    """Manages multiple protocol adapters and routes messages"""
    
    def __init__(self):
        self.protocols: Dict[str, AgentProtocol] = {}
        self.default_protocol: Optional[str] = None
    
    def register(self, protocol: AgentProtocol):
        """Register a protocol adapter
        
        Args:
            protocol: Protocol adapter instance
        """
        name = protocol.get_protocol_name()
        self.protocols[name] = protocol
        
        # First registered protocol becomes default
        if self.default_protocol is None:
            self.default_protocol = name
        
        print(f"Registered protocol: {name}")
    
    def get_protocol(self, name: str) -> Optional[AgentProtocol]:
        """Get protocol by name
        
        Args:
            name: Protocol name (a2a, slim, etc.)
            
        Returns:
            Protocol adapter or None
        """
        return self.protocols.get(name)
    
    def get_all_protocols(self) -> List[str]:
        """Get list of all registered protocol names"""
        return list(self.protocols.keys())
    
    async def send(self, protocol_name: str, target_url: str, message: dict) -> dict:
        """Send message using specified protocol
        
        Args:
            protocol_name: Protocol to use (a2a, slim)
            target_url: Target agent endpoint
            message: Message to send
            
        Returns:
            Response from target agent
            
        Raises:
            ValueError: If protocol not registered
        """
        protocol = self.protocols.get(protocol_name)
        if not protocol:
            raise ValueError(f"Protocol '{protocol_name}' not registered. "
                           f"Available: {list(self.protocols.keys())}")
        
        return await protocol.send_message(target_url, message)
    
    def select_protocol(self, supported_protocols: List[str]) -> str:
        """Select best available protocol from supported list
        
        Args:
            supported_protocols: List of protocols target agent supports
            
        Returns:
            Selected protocol name
        """
        # Try to find first match from supported list
        for proto in supported_protocols:
            if proto in self.protocols:
                return proto
        
        # Fallback to default if no match
        if self.default_protocol:
            return self.default_protocol
        
        # Last resort: use first registered protocol
        if self.protocols:
            return list(self.protocols.keys())[0]
        
        raise ValueError("No protocols registered")
    
    async def start_all_servers(self, host: str, port: int):
        """Start all registered protocol servers

        Note: For protocols that need different ports, override in protocol adapter

        Args:
            host: Host to bind to
            port: Base port (protocols may use port+offset)
        """
        for name, protocol in self.protocols.items():
            print(f"Starting {name} protocol server...")
            # Each protocol handles its own server startup
            # They can use different ports internally
            await protocol.start_server(host, port)

    async def cleanup_all(self):
        """Clean up all registered protocol resources

        Called when agent is stopping to ensure all protocols
        properly release their resources (HTTP clients, connections, etc.)
        """
        for name, protocol in self.protocols.items():
            try:
                await protocol.cleanup()
            except Exception as e:
                print(f"⚠️  Error cleaning up {name} protocol: {e}")