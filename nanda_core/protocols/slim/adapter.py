"""
SLIM Protocol Adapter - Secure Low-latency Interactive Messaging

Provides gRPC-based messaging with persistent connections.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Callable, Dict, Any, Optional
import grpc

logger = logging.getLogger(__name__)

try:
    # Import SLIM SDK components
    from slim_bindings.slim import Slim, PyName, PyIdentityProvider, PyIdentityVerifier
    from slim_bindings.session import PySession, PySessionConfiguration, PyMessageContext
    SLIM_AVAILABLE = True
except ImportError:
    SLIM_AVAILABLE = False
    logger.warning("slim-bindings not available. Install with: pip install slim-bindings")

from ..base import AgentProtocol


class SLIMProtocol(AgentProtocol):
    """SLIM Protocol adapter for gRPC-based agent communication"""
    
    def __init__(self, agent_id: str, slim_node_url: str, agent_name: str = None):
        """Initialize SLIM protocol adapter
        
        Args:
            agent_id: Unique agent identifier
            slim_node_url: SLIM node gRPC endpoint (e.g., grpc://localhost:50051)
            agent_name: Optional agent display name
        """
        if not SLIM_AVAILABLE:
            raise ImportError("slim-bindings not installed. Run: pip install slim-bindings")
        
        self.agent_id = agent_id
        # Ensure URL has http:// prefix (required by SLIM SDK)
        if not slim_node_url.startswith('http://') and not slim_node_url.startswith('https://'):
            slim_node_url = f'http://{slim_node_url}'
        self.slim_node_url = slim_node_url.replace('grpc://', 'http://')
        self.agent_name = agent_name or agent_id
        
        # Message handler (set by bridge)
        self.incoming_handler: Optional[Callable] = None
        
        # SLIM client
        self.slim: Optional[Slim] = None
        self.session: Optional[PySession] = None
        self.stream_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Personal inbox channel name
        self.inbox_channel = f"agent-{agent_id}-inbox"
        
        print(f"SLIM protocol initialized for {agent_id} at {self.slim_node_url}")
    
    def set_incoming_handler(self, handler: Callable):
        """Set callback for incoming messages"""
        self.incoming_handler = handler
        print(f"Incoming handler set for SLIM protocol")
    
    async def connect(self):
        """Connect to SLIM node and subscribe to inbox"""
        try:
            # Connect to SLIM node
            print(f"Connecting to SLIM node at {self.slim_node_url}...")

            # Create PyName
            name = PyName("agntcy", "nanda", self.agent_id)

            # Create identity provider and verifier
            provider = PyIdentityProvider.SharedSecret(
                identity=self.agent_id,
                shared_secret="nanda-dev-secret"  # TODO: Use env var
            )
            verifier = PyIdentityVerifier.SharedSecret(
                identity=self.agent_id,
                shared_secret="nanda-dev-secret"  # TODO: Use env var
            )

            # Initialize Slim
            self.slim = await Slim.new(name, provider, verifier)
            print(f"✅ Slim instance created with ID: {self.slim.id}")

            # Connect to SLIM node
            conn_id = await self.slim.connect({"endpoint": self.slim_node_url, "tls": {"insecure": True}})
            print(f"✅ Connected to SLIM node (connection ID: {conn_id})")            
            
            # Start listening for incoming sessions
            self.running = True
            self.stream_task = asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to SLIM node: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _listen_for_messages(self):
        """Listen for incoming sessions"""
        print(f"👂 Listening for incoming SLIM sessions")
        
        try:
            while self.running:
                try:
                    print(f"⏳ Waiting for incoming session...")
                    
                    # Wait for incoming session
                    session = await self.slim.listen_for_session()
                    print(f"📬 Got incoming session: {session.id}")
                    
                    # Handle session in background task
                    asyncio.create_task(self._handle_session(session))
                    
                except Exception as e:
                    logger.error(f"Error in session listener: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            print("SLIM message listener cancelled")
    
    async def _handle_session(self, session):
        """Handle a single session (can receive multiple messages)"""
        try:
            while True:
                # Receive message
                msg_ctx, payload_bytes = await session.get_message()
                print(f"📥 SLIM: Received {len(payload_bytes)} bytes")
                
                # Process message
                await self._process_incoming_message(session, msg_ctx, payload_bytes)
                
        except Exception as e:
            print(f"Session {session.id} ended: {e}")
    
    async def _process_incoming_message(self, session, msg_ctx, payload_bytes: bytes):
        """Process incoming SLIM message and route to handler"""
        try:
            # Decode payload
            try:
                payload_str = payload_bytes.decode('utf-8')
                payload_data = json.loads(payload_str)
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload_str = payload_bytes.decode('utf-8', errors='replace')
                payload_data = {"text": payload_str}
            
            # Convert to standard NANDA message format
            message_dict = {
                "content": {
                    "text": payload_data.get("text", payload_str),
                    "type": "text"
                },
                "conversation_id": "slim-conversation",
                "metadata": {
                    "protocol": "slim",
                    "session_id": session.id
                }
            }
            
            print(f"📥 SLIM message: {message_dict['content']['text'][:100]}")
            
            # Call handler
            if self.incoming_handler:
                response = await self.incoming_handler(message_dict)
                print(f"🤖 Agent response: {response.get('content', {}).get('text', '')[:100]}...")  # <-- ADD THIS
                
                # Send response back
                if response:
                    await self._send_response(session, msg_ctx, response)
            
        except Exception as e:
            logger.error(f"❌ Error processing SLIM message: {e}")
            import traceback
            traceback.print_exc()
    
    async def _send_response(self, session, msg_ctx, response: Dict[str, Any]):
        """Send response back using publish_to"""
        try:
            response_text = response.get("content", {}).get("text", "")
            
            response_payload = {
                "text": response_text,
                "type": "response"
            }
            
            await session.publish_to(msg_ctx, json.dumps(response_payload).encode('utf-8'))
            print(f"📤 SLIM: Sent response")
            
        except Exception as e:
            logger.error(f"Error sending SLIM response: {e}")
    
    async def send_message(self, target_url: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message via SLIM protocol"""
        try:
            if not self.slim:
                raise RuntimeError("SLIM not connected")
            
            # Extract target agent ID
            target_agent_id = target_url.replace('slim://', '').split('/')[0]
            content_text = message.get("content", {}).get("text", "")
            
            print(f"📤 SLIM: Sending to {target_agent_id}: {content_text[:50]}...")
            
            # Create message payload
            payload = {"text": content_text, "type": "message"}
            
            # Set route to target
            target_name = PyName("agntcy", "nanda", target_agent_id)
            await self.slim.set_route(target_name)
            
            # Create PointToPoint session
            from datetime import timedelta
            config = PySessionConfiguration.PointToPoint(
                peer_name=target_name,
                timeout=timedelta(seconds=5),
                max_retries=5,
                mls_enabled=False
            )
            
            session = await self.slim.create_session(config)
            
            # Send message
            await session.publish(json.dumps(payload).encode('utf-8'))
            print(f"✅ SLIM: Message sent")
            
            # Wait for reply
            msg_ctx, reply_bytes = await session.get_message()
            reply_data = json.loads(reply_bytes.decode('utf-8'))
            
            # Clean up
            await session.delete()
            
            return {
                "content": {
                    "text": reply_data.get("text", reply_bytes.decode('utf-8')),
                    "type": "text"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error sending SLIM message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "content": {
                    "text": f"SLIM Error: {str(e)}",
                    "type": "text"
                }
            }
    
    async def handle_request(self, request):
        """Handle incoming request (not used for SLIM - uses streaming)"""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get SLIM protocol metadata"""
        return {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "protocol": "slim",
            "slim_node": self.slim_node_url,
            "inbox_channel": self.inbox_channel,
            "capabilities": ["unicast", "async_messaging"]
        }
    
    async def start_server(self, host: str, port: int):
        """Start SLIM protocol (connect and listen)"""
        print(f"🚀 Starting SLIM protocol for {self.agent_id}")
        
        # Connect to SLIM node
        await self.connect()
        
        print(f"✅ SLIM ready - listening on {self.inbox_channel}")
        
        # Keep running (stream_task handles incoming messages)
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("SLIM protocol stopped")
        finally:
            await self.close()
    
    async def close(self):
        """Close SLIM connection and cleanup"""
        print(f"🛑 Closing SLIM connection for {self.agent_id}")
        
        self.running = False
        
        if self.stream_task:
            self.stream_task.cancel()
            try:
                await self.stream_task
            except asyncio.CancelledError:
                pass
        
        if self.slim:
            try:
                await self.slim.disconnect(self.slim_node_url)
            except Exception as e:
                logger.error(f"Error disconnecting SLIM: {e}")
    
    def get_protocol_name(self) -> str:
        """Return protocol identifier"""
        return "slim"