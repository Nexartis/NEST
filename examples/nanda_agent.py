# examples/nanda_agent.py
#!/usr/bin/env python3
"""
LLM-Powered NANDA Agent

Configurable agent using Anthropic Claude for intelligent responses.
Customize via environment variables or the config dict.
"""
import os
import sys
import asyncio
import uuid
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanda_core.core.adapter import NANDA

from dotenv import load_dotenv
load_dotenv()

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ anthropic library not available. Install with: pip install anthropic")

# =============================================================================
# CONFIGURATION
# =============================================================================

def get_config():
    """Load configuration from environment variables"""
    base_id = os.getenv("AGENT_ID", "helpful-agent")
    agent_id = f"{base_id}-{uuid.uuid4().hex[:6]}" if '-' not in base_id else base_id
    
    capabilities = os.getenv("AGENT_CAPABILITIES", "general assistance,conversation")
    capabilities_list = [cap.strip() for cap in capabilities.split(",")]
    
    agent_name = os.getenv("AGENT_NAME", "Helper Agent")
    domain = os.getenv("AGENT_DOMAIN", "general assistance")
    specialization = os.getenv("AGENT_SPECIALIZATION", "helpful AI assistant")
    description = os.getenv("AGENT_DESCRIPTION", "I'm a helpful AI assistant.")
    
    system_prompt = f"""You are {agent_name}, a {specialization} in {domain}.

{description}

You are part of the NANDA agent network and can communicate with other agents using @agent-id syntax.

Your capabilities: {', '.join(capabilities_list)}

Be helpful, accurate, and concise."""

    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "domain": domain,
        "specialization": specialization,
        "description": description,
        "capabilities": capabilities_list,
        "port": int(os.getenv("PORT", "6000")),
        "registry_url": os.getenv("REGISTRY_URL"),
        "public_url": os.getenv("PUBLIC_URL") or f"http://localhost:{os.getenv('PORT', '6000')}",
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        "system_prompt": system_prompt,
        "protocols": {
            "a2a": {"enabled": True},
            "slim": {
                "enabled": os.getenv("SLIM_ENABLED", "false").lower() == "true",
                "node_url": os.getenv("SLIM_NODE_URL", "grpc://localhost:50051")
            }
        }
    }

# =============================================================================
# AGENT LOGIC
# =============================================================================

def create_agent_logic(config):
    """Create agent logic function with LLM or fallback"""
    
    # Initialize Anthropic client
    client = None
    if ANTHROPIC_AVAILABLE and config.get("anthropic_api_key"):
        try:
            client = Anthropic(api_key=config["anthropic_api_key"])
            print(f"✅ Claude initialized ({config['model']})")
        except Exception as e:
            print(f"❌ Claude initialization failed: {e}")
    
    def agent_logic(message: str, conversation_id: str) -> str:
        """Process message with Claude or fallback"""
        
        if client:
            try:
                # Add time context if relevant
                context = ""
                if any(word in message.lower() for word in ['time', 'date', 'when']):
                    context = f"\n\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                response = client.messages.create(
                    model=config["model"],
                    max_tokens=500,
                    system=config["system_prompt"] + context,
                    messages=[{"role": "user", "content": message}]
                )
                
                return response.content[0].text.strip()
                
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Fallback responses
        msg = message.lower().strip()
        if any(greeting in msg for greeting in ['hello', 'hi', 'hey']):
            return f"Hello! I'm {config['agent_name']}. Set ANTHROPIC_API_KEY for full capabilities."
        elif 'time' in msg:
            return f"Current time: {datetime.now().strftime('%H:%M:%S')}"
        else:
            return f"I'm {config['agent_name']}. Set ANTHROPIC_API_KEY to enable LLM responses."
    
    return agent_logic

# =============================================================================
# MAIN
# =============================================================================

async def main():
    config = get_config()
    
    print(f"🤖 {config['agent_name']} ({config['agent_id']})")
    print(f"🎯 {config['domain']} - {config['specialization']}")
    print(f"🔗 {config['public_url']}/a2a")
    if config['registry_url']:
        print(f"🌐 Registry: {config['registry_url']}")
    
    agent_logic = create_agent_logic(config)
    
    nanda = NANDA(
        agent_id=config["agent_id"],
        agent_logic=agent_logic,
        agent_name=config["agent_name"],
        domain=config["domain"],
        specialization=config["specialization"],
        description=config["description"],
        capabilities=config["capabilities"],
        port=config["port"],
        registry_url=config["registry_url"],
        public_url=config["public_url"],
        enable_telemetry=True,
        protocols=config["protocols"]
    )
    
    print("\n💬 Try: 'Hello', 'What time is it?', '@other-agent Hello!'")
    print("🛑 Press Ctrl+C to stop\n")
    
    await nanda.start()

if __name__ == "__main__":
    asyncio.run(main())