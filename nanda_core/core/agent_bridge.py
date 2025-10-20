"""
Agent Bridge for Protocol-Agnostic Communication

Handles message routing between agents using any registered protocol.
"""

import re
import uuid
import logging
from typing import Callable, Optional, Dict, Any
from ..protocols.router import ProtocolRouter
from .registry_client import RegistryClient

logger = logging.getLogger(__name__)


class AgentBridge:
    """Protocol-agnostic agent message router and coordinator"""
    
    def __init__(self, 
                 protocol_router: ProtocolRouter,
                 registry_client: RegistryClient,
                 agent_id: str,
                 agent_logic: Callable[[str, str], str],
                 telemetry=None):
        """Initialize agent bridge
        
        Args:
            protocol_router: Router managing protocol adapters
            registry_client: Client for NANDA Index
            agent_id: This agent's unique identifier
            agent_logic: Agent's business logic function(message: str, conversation_id: str) -> str
            telemetry: Optional telemetry system
        """
        self.router = protocol_router
        self.registry = registry_client
        self.agent_id = agent_id
        self.agent_logic = agent_logic
        self.telemetry = telemetry
        
        # Register this bridge as incoming handler for all protocols
        for protocol_name in self.router.get_all_protocols():
            protocol = self.router.get_protocol(protocol_name)
            protocol.set_incoming_handler(self.handle_message)
        
        logger.info(f"🌉 Bridge initialized for {agent_id} with protocols: {self.router.get_all_protocols()}")
    
    def extract_agent_id(self, content: str) -> Optional[str]:
        """Extract @agent-id from message content"""
        match = re.search(r'@([\w-]+)', content)
        return match.group(1) if match else None
    
    def parse_incoming_agent_message(self, text: str) -> Optional[Dict[str, str]]:
        """Parse incoming agent-to-agent message in format:
        FROM: sender\nTO: receiver\nMESSAGE: content
        """
        if not (text.startswith("FROM:") and "TO:" in text and "MESSAGE:" in text):
            return None
        
        try:
            lines = text.strip().split('\n')
            result = {}
            
            for line in lines:
                if line.startswith("FROM:"):
                    result['from_agent'] = line[5:].strip()
                elif line.startswith("TO:"):
                    result['to_agent'] = line[3:].strip()
                elif line.startswith("MESSAGE:"):
                    result['message'] = line[8:].strip()
            
            return result if all(k in result for k in ['from_agent', 'to_agent', 'message']) else None
        except Exception as e:
            logger.error(f"Error parsing agent message: {e}")
            return None
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handling entry point
        
        Called by protocol adapters when messages arrive.
        """
        content = message.get("content", {}).get("text", "")
        conversation_id = message.get("conversation_id", "") or str(uuid.uuid4())
        
        # Check if this is an incoming agent-to-agent message
        parsed = self.parse_incoming_agent_message(content)
        if parsed:
            return await self._handle_incoming_agent_message(parsed, conversation_id)
        
        logger.info(f"📨 [{self.agent_id}] Received: {content}")
        
        try:
            # Check message type
            if content.startswith("@"):
                # Outgoing agent-to-agent message
                return await self._handle_outgoing_agent_message(content, conversation_id)
            elif content.startswith("/"):
                # System command
                return await self._handle_command(content, conversation_id)
            else:
                # Regular message - use agent logic
                if self.telemetry:
                    self.telemetry.log_message_received(self.agent_id, conversation_id)
                
                response = self.agent_logic(content, conversation_id)
                return self._create_response(response)
                
        except Exception as e:
            logger.error(f"❌ [{self.agent_id}] Error handling message: {e}")
            return self._create_response(f"Error: {str(e)}")
    
    async def _handle_incoming_agent_message(self, parsed: Dict[str, str], 
                                            conversation_id: str) -> Dict[str, Any]:
        """Handle incoming messages from other agents"""
        from_agent = parsed['from_agent']
        message_content = parsed['message']
        
        logger.info(f"📨 [{self.agent_id}] ← [{from_agent}]: {message_content}")
        
        # Check if this is a reply (avoid infinite loops)
        if message_content.startswith("Response to "):
            logger.info(f"🔄 [{self.agent_id}] Received reply from {from_agent}")
            return self._create_response(f"[{from_agent}] {message_content[len(f'Response to {self.agent_id}: '):]}")
        
        # Process through agent logic
        if self.telemetry:
            self.telemetry.log_message_received(self.agent_id, conversation_id)
        
        response = self.agent_logic(message_content, conversation_id)
        return self._create_response(f"Response to {from_agent}: {response}")
    
    async def _handle_outgoing_agent_message(self, content: str, 
                                            conversation_id: str) -> Dict[str, Any]:
        """Handle messages to other agents (@agent_id message)"""
        parts = content.split(" ", 1)
        if len(parts) <= 1:
            return self._create_response("Invalid format. Use '@agent_id message'")
        
        target_agent_id = parts[0][1:]  # Remove @
        message_text = parts[1]
        
        logger.info(f"🔄 [{self.agent_id}] Sending to {target_agent_id}: {message_text}")
        
        # Route to target agent
        result = await self.route_to_agent(target_agent_id, message_text, conversation_id)
        return result
    
    async def _handle_command(self, content: str, conversation_id: str) -> Dict[str, Any]:
        """Handle system commands"""
        parts = content.split(" ", 1)
        command = parts[0][1:] if len(parts) > 0 else ""
        
        if command == "help":
            help_text = """Available commands:
/help - Show this help
/ping - Test agent responsiveness  
/status - Show agent status
@agent_id message - Send message to another agent"""
            return self._create_response(help_text)
        
        elif command == "ping":
            return self._create_response("Pong!")
        
        elif command == "status":
            protocols = self.router.get_all_protocols()
            status = f"Agent: {self.agent_id}, Status: Running, Protocols: {', '.join(protocols)}"
            if hasattr(self.registry, 'registry_url') and self.registry.registry_url:
                status += f", Registry: {self.registry.registry_url}"
            return self._create_response(status)
        
        else:
            return self._create_response(
                f"Unknown command: {command}. Use /help for available commands"
            )
    
    async def route_to_agent(self, target_agent_id: str, message_text: str,
                        conversation_id: str) -> Dict[str, Any]:
        """Route message to target agent via appropriate protocol"""
        try:
            # Resolve agent via NANDA Index
            agent_info = await self.registry.resolve(target_agent_id)
            
            if not agent_info:
                logger.warning(f"🔍 Agent {target_agent_id} not found in registry")
                return self._create_response(f"Agent {target_agent_id} not found")
            protocol_name = "slim"  # <-- Force SLIM
            target_url = f"slim://{target_agent_id}"  # <-- Force SLIM URL
            
            logger.info(f"🧪 TEST MODE: Forcing SLIM protocol")
            logger.info(f"📤 [{self.agent_id}] → [{target_agent_id}] via {protocol_name}")
            logger.info(f"🔗 Target URL: {target_url}")

            # Debug: print what we got from registry
            logger.info(f"📋 Agent info from registry: {agent_info}")
            
            # Select protocol
            supported_protocols = agent_info.get("supported_protocols") or self.router.get_all_protocols()
            protocol_name = self.router.select_protocol(supported_protocols)
            
            # Get target URL - try multiple fields
            endpoints = agent_info.get("endpoints", {})
            target_url = endpoints.get(protocol_name)
            
            if not target_url:
                # Fallback logic
                if protocol_name == "slim":
                    # For SLIM, construct the identifier
                    target_url = f"slim://{target_agent_id}"
                else:
                    # For A2A, use URL fields
                    target_url = (
                        agent_info.get("url") or 
                        agent_info.get("agent_url") or 
                        agent_info.get("public_url")
                    )

            # Ensure target_url is valid
            if not target_url:
                logger.error(f"❌ No URL found for {target_agent_id}. Agent info: {agent_info}")
                return self._create_response(f"No endpoint found for {target_agent_id}")
            
            # Add /a2a suffix if needed and not already present
            if protocol_name == "a2a" and not target_url.endswith('/a2a'):
                target_url = f"{target_url}/a2a"
            
            logger.info(f"📤 [{self.agent_id}] → [{target_agent_id}] via {protocol_name}: {message_text}")
            logger.info(f"🔗 Target URL: {target_url}")
            
            # Create message in simple format
            simple_message = f"FROM: {self.agent_id}\nTO: {target_agent_id}\nMESSAGE: {message_text}"
            
            # Send via protocol
            message = {
                "content": {
                    "text": simple_message,
                    "type": "text"
                },
                "conversation_id": conversation_id,
                "metadata": {
                    "from_agent_id": self.agent_id,
                    "to_agent_id": target_agent_id,
                    "message_type": "agent_to_agent"
                }
            }
            
            response = await self.router.send(protocol_name, target_url, message)
            
            if self.telemetry:
                self.telemetry.log_message_sent(target_agent_id, conversation_id)
            
            # Extract response
            response_text = response.get("content", {}).get("text", str(response))
            logger.info(f"✅ [{self.agent_id}] Response from {target_agent_id}: {response_text[:100]}...")
            
            return self._create_response(f"[{target_agent_id}] {response_text}")
            
        except Exception as e:
            logger.error(f"❌ Error routing to {target_agent_id}: {e}")
            import traceback
            traceback.print_exc()
            return self._create_response(f"❌ Error sending to {target_agent_id}: {str(e)}")
    
    def _create_response(self, text: str) -> Dict[str, Any]:
        """Create a standardized response dict"""
        return {
            "content": {
                "text": f"[{self.agent_id}] {text}",
                "type": "text"
            }
        }
    
    async def run_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start all protocol servers"""
        logger.info(f"🚀 Starting agent bridge for {self.agent_id} on {host}:{port}")
        await self.router.start_all_servers(host, port)