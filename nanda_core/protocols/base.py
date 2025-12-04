from abc import ABC, abstractmethod
from typing import Callable, Dict, Any

class AgentProtocol(ABC):
    """Base protocol interface for agent communication"""
    
    @abstractmethod
    async def send_message(self, target_url: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to target agent
        
        Args:
            target_url: Target agent's endpoint URL
            message: Message dict with 'content', 'conversation_id', etc.
            
        Returns:
            Response dict from target agent
        """
        pass
    
    @abstractmethod
    def set_incoming_handler(self, handler: Callable):
        """Set callback for incoming messages
        
        Args:
            handler: Async function that processes incoming messages
                    Should accept message dict and return response dict
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get protocol-specific agent metadata (AgentCard, etc.)
        
        Returns:
            Metadata dict for agent discovery
        """
        pass
    
    @abstractmethod
    async def start_server(self, host: str, port: int):
        """Start protocol server
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        pass
    
    @abstractmethod
    def get_protocol_name(self) -> str:
        """Return protocol identifier (a2a, slim, etc.)"""
        pass

    @abstractmethod
    async def cleanup(self):
        """Clean up protocol resources (HTTP clients, connections, etc.)

        Called when agent is stopping to ensure proper resource cleanup.
        """
        pass