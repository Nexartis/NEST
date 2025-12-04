"""
Official A2A SDK Protocol Adapter
"""

from typing import Callable, Dict, Any
from a2a.client import A2AClient, ClientConfig, ClientFactory
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCard, AgentSkill, AgentCapabilities, AgentInterface,
    Message, TextPart, Part, Role,
    SendMessageRequest, MessageSendParams,
    TransportProtocol
)
import uuid
import httpx
import uvicorn
from ..base import AgentProtocol
from ..AgentExecutor import NANDAAgentExecutor

class A2AProtocol(AgentProtocol):
    """A2A SDK protocol adapter"""
    
    def __init__(self, agent_id: str, agent_name: str, public_url: str,
                 domain: str = None, specialization: str = None,
                 description: str = "", capabilities: list = None):
        """Initialize A2A protocol adapter
        
        Args:
            agent_id: Unique agent identifier
            agent_name: Display name
            public_url: Public URL where agent is accessible
            domain: Agent's domain of expertise
            specialization: Agent's specialization
            description: Agent description
            capabilities: List of capabilities (default: ["text"])
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.public_url = public_url
        self.description = description
        self.capabilities_list = capabilities or ["text"]
        
        # Create AgentCard
        self.agent_card = AgentCard(
            name=agent_name,
            description=description,
            version="1.0.0",
            url=f"{public_url}/",
            protocol_version="0.2.5",
            skills=[
                AgentSkill(
                    id=agent_id,
                    name=agent_name,
                    description=description,
                    tags=[domain] if domain else [],
                    examples=[]
                )
            ],
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=False
            ),
            defaultInputModes=["text"],
            defaultOutputModes=["text"]
        )
        
        # Incoming message handler (set by bridge)
        self.incoming_handler: Callable = None
        
        # Server components (initialized when handler is set)
        self.agent_executor = None
        self.request_handler = None
        self.server_app = None
        
        # HTTP client for A2A client
        self.httpx_client = httpx.AsyncClient()
    
    def set_incoming_handler(self, handler: Callable):
        """Set callback for incoming messages
        
        Args:
            handler: Async function(message: dict) -> dict
        """
        self.incoming_handler = handler
        
        # Initialize server components
        self.agent_executor = NANDAAgentExecutor(handler)
        self.request_handler = DefaultRequestHandler(
            agent_executor=self.agent_executor,
            task_store=InMemoryTaskStore()
        )
        self.server_app = A2AStarletteApplication(
            agent_card=self.agent_card,
            http_handler=self.request_handler
        )
    
    async def send_message(self, target_url: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message using A2A client"""
        try:
            # Validate target_url
            if not target_url:
                raise ValueError("target_url is None or empty")
            
            # Extract message content
            content_text = message.get("content", {}).get("text", "")
            conversation_id = message.get("conversation_id", "")
            metadata = message.get("metadata", {})
            
            print(f"🔄 Sending to {target_url}: {content_text[:50]}...")
            
            # Create A2A message with proper structure
            from a2a.types import TextPart, Part, Message, Role
            
            text_part = TextPart(
                kind='text',
                text=content_text
            )
            part = Part(root=text_part)
            
            a2a_message = Message(
                message_id=f"msg-{conversation_id}-{uuid.uuid4().hex[:8]}",
                role=Role.user,
                parts=[part],
                metadata=metadata if metadata else None
            )
            
            # Get client - strip /a2a suffix if present
            base_url = target_url.rstrip('/a2a') if target_url else target_url

            client = A2AClient(
                httpx_client=self.httpx_client,
                url=base_url  # Just pass the base URL
            )
            
            # Create request
            from a2a.types import SendMessageRequest, MessageSendParams
            request = SendMessageRequest(
                id=f"req-{uuid.uuid4().hex[:8]}",
                params=MessageSendParams(message=a2a_message)
            )
            
            # Send message
            response = await client.send_message(request)
            print(f"🔍 Response attributes: {dir(response)}")
            print(f"🔍 Response dict: {response.model_dump() if hasattr(response, 'model_dump') else response}")
            
            if hasattr(response, 'root'):
                result = response.root
                
                # Check if it's an error response
                if hasattr(result, 'error') and result.error:
                    error_msg = result.error.message if hasattr(result.error, 'message') else str(result.error)
                    return {
                        "content": {
                            "text": f"Error: {error_msg}",
                            "type": "text"
                        }
                    }
                
                # Check if it's a success response with result
                if hasattr(result, 'result'):
                    msg = result.result
                    if hasattr(msg, 'parts') and msg.parts:
                        response_text = ""
                        for part in msg.parts:
                            part_obj = part.root if hasattr(part, 'root') else part
                            if hasattr(part_obj, 'text'):
                                response_text = part_obj.text
                                break
                        
                        return {
                            "content": {
                                "text": response_text,
                                "type": "text"
                            }
                        }

            return {
                "content": {
                    "text": "No response received",
                    "type": "text"
                }
            }
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "content": {
                    "text": f"Error: {str(e)}",
                    "type": "text"
                }
            }    
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get AgentCard metadata
        
        Returns:
            AgentCard as dict
        """
        return {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "url": self.agent_card.url,
            "description": self.description,
            "capabilities": self.capabilities_list
        }
    
    async def start_server(self, host: str, port: int):
        """Start A2A server
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        if not self.server_app:
            raise RuntimeError("Server not initialized. Call set_incoming_handler first.")
        
        print(f"Starting A2A server on {host}:{port}")
        
        # Build Starlette app
        app = self.server_app.build()
        
        # Run with uvicorn
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_protocol_name(self) -> str:
        """Return protocol identifier"""
        return "a2a"

    async def cleanup(self):
        """Clean up A2A protocol resources"""
        if self.httpx_client:
            await self.httpx_client.aclose()
            print(f"🧹 Closed HTTP client for A2A protocol")