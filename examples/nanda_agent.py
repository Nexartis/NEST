#!/usr/bin/env python3
"""
LLM-Powered Modular NANDA Agent

This agent uses Anthropic Claude for intelligent responses based on configurable personality and expertise.
Simply update the AGENT_CONFIG section to create different agent personalities.
"""
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any

# Add the parent directory to the path to allow importing streamlined_adapter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanda_core.core.adapter import NANDA

from dotenv import load_dotenv
load_dotenv()

# Try to import Anthropic - will fail gracefully if not available
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ Warning: anthropic library not available. Install with: pip install anthropic")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# =============================================================================
# AGENT CONFIGURATION - Customize this section for different agents
# =============================================================================

# Get configuration from environment variables or use defaults
def get_agent_config():
    """Load agent configuration from environment variables or use defaults"""
    
    # Generate agent_id with hex suffix for uniqueness
    base_agent_id = os.getenv("AGENT_ID", "helpful-ubuntu-agent")
    if not base_agent_id.endswith('-') and '-' not in base_agent_id.split('-')[-1]:
        # Add 6-character hex suffix if not already present
        hex_suffix = uuid.uuid4().hex[:6]
        agent_id = f"{base_agent_id}-{hex_suffix}"
    else:
        agent_id = base_agent_id
    
    print(f"Generated agent_id: {agent_id}")
    agent_name = os.getenv("AGENT_NAME", "Ubuntu Helper")
    domain = os.getenv("AGENT_DOMAIN", "general assistance")
    specialization = os.getenv("AGENT_SPECIALIZATION", "helpful and friendly AI assistant")
    description = os.getenv("AGENT_DESCRIPTION", "I am a helpful AI assistant specializing in general tasks and Ubuntu system administration.")
    capabilities = os.getenv("AGENT_CAPABILITIES", "general assistance,Ubuntu system administration,Python development,cloud deployment,agent-to-agent communication")
    registry_url = os.getenv("REGISTRY_URL", None)
    mcp_registry_url = os.getenv("MCP_REGISTRY_URL", None)
    public_url = os.getenv("PUBLIC_URL", None)
    
    # LLM Configuration - NEW
    llm_provider = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic, openai, gemini

    print("LLM_PROVIDER", llm_provider)

    # Get API key based on provider
    if os.getenv("LLM_API_KEY"):
        llm_api_key = os.getenv("LLM_API_KEY")
    elif llm_provider == "anthropic":
        llm_api_key = os.getenv("ANTHROPIC_API_KEY")
    elif llm_provider == "openai":
        llm_api_key = os.getenv("OPENAI_API_KEY")
    elif llm_provider == "gemini":
        llm_api_key = os.getenv("GOOGLE_API_KEY")
    else:
        llm_api_key = None
    
    print("api key", llm_api_key)
    # Default models per provider
    default_models = {
        "anthropic": "claude-3-haiku-20240307",
        "openai": "gpt-4",
        "gemini": "gemini-2.5-flash-lite"
    }
    llm_model = os.getenv("LLM_MODEL", default_models.get(llm_provider, "claude-3-haiku-20240307"))

    # Parse capabilities into a list
    expertise_list = [cap.strip() for cap in capabilities.split(",")]
    
    # Create dynamic system prompt based on configuration
    system_prompt = f"""You are {agent_name}, a {specialization} working in the domain of {domain}.

{description}

You are part of the NANDA (Network of Autonomous Distributed Agents) system. You can communicate with other agents and help users with various tasks.

Your capabilities include:
{chr(10).join([f"- {cap}" for cap in expertise_list])}

Always be helpful, accurate, and concise in your responses. If you're unsure about something, say so honestly. You can also help with basic calculations, provide time information, and engage in casual conversation.

When someone asks about yourself, mention that you're part of the NANDA agent network and can communicate with other agents using the @agent_name syntax."""

    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "domain": domain,
        "specialization": specialization,
        "description": description,
        "expertise": expertise_list,
        "registry_url": registry_url,
        "mcp_registry_url": mcp_registry_url,
        "public_url": public_url,
        "system_prompt": system_prompt,
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "llm_provider": llm_provider,      # NEW
        "llm_api_key": llm_api_key,        # NEW
        "llm_model": llm_model,            # NEW
        "model": llm_model  # Alias
    }

# Load configuration
AGENT_CONFIG = get_agent_config()

# Port configuration - use environment variable or default to 6000
PORT = int(os.getenv("PORT", "6000"))

# =============================================================================
# LLM-POWERED AGENT LOGIC - Uses Anthropic Claude for intelligent responses
# =============================================================================

def create_llm_agent_logic(config: Dict[str, Any]):
    """
    Creates an LLM-powered agent logic function based on the provided configuration.
    Uses Anthropic Claude for intelligent, context-aware responses.
    """
    
    # Initialize Anthropic client
    llm_client = None
    provider = config.get("llm_provider", "anthropic")
    system_prompt = config["system_prompt"]

    # Initialize appropriate LLM client
    print(f"GEMINI_AVAILABLE: {GEMINI_AVAILABLE}")

    if provider == "anthropic" and ANTHROPIC_AVAILABLE and config.get("llm_api_key"):
        try:
            llm_client = Anthropic(api_key=config["llm_api_key"])
            print(f"✅ Anthropic Claude initialized")
        except Exception as e:
            print(f"❌ Anthropic init failed: {e}")
    
    elif provider == "openai" and OPENAI_AVAILABLE and config.get("llm_api_key"):
        try:
            llm_client = OpenAI(api_key=config["llm_api_key"])
            print(f"✅ OpenAI GPT initialized")
        except Exception as e:
            print(f"❌ OpenAI init failed: {e}")
    
    elif provider == "gemini" and GEMINI_AVAILABLE and config.get("llm_api_key"):
        try:
            genai.configure(api_key=config["llm_api_key"])
            llm_client = genai.GenerativeModel(config["llm_model"])
            print(f"✅ Google Gemini initialized")
        except Exception as e:
            print(f"❌ Gemini init failed: {e}")
    
    def llm_agent_logic(message: str, conversation_id: str) -> str:
        """LLM-powered agent logic with fallback to basic responses"""
        
        if llm_client:
            try:
                context_info = ""
                if any(time_word in message.lower() for time_word in ['time', 'date', 'when']):
                    context_info = f"\n\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                full_prompt = system_prompt + context_info
                
                # Call appropriate LLM
                if provider == "anthropic":
                    response = llm_client.messages.create(
                        model=config["llm_model"],
                        max_tokens=500,
                        system=full_prompt,
                        messages=[{"role": "user", "content": message}]
                    )
                    return response.content[0].text.strip()
                
                elif provider == "openai":
                    response = llm_client.chat.completions.create(
                        model=config["llm_model"],
                        max_tokens=500,
                        messages=[
                            {"role": "system", "content": full_prompt},
                            {"role": "user", "content": message}
                        ]
                    )
                    return response.choices[0].message.content.strip()
                
                elif provider == "gemini":
                    print("in the gemini if")
                    response = llm_client.generate_content(
                        f"{full_prompt}\n\nUser: {message}",
                        generation_config=genai.GenerationConfig(max_output_tokens=500)
                    )
                    return response.text.strip()
                    
            except Exception as e:
                print(f"❌ LLM Error: {e}")
                return f"Sorry, I'm having trouble processing that right now. Error: {str(e)}"
        
        # Fallback to basic response
        else:
            return _basic_fallback_response(message, config)
    
    return llm_agent_logic

def _basic_fallback_response(message: str, config: Dict[str, Any]) -> str:
    """Basic fallback responses when LLM is not available"""
    msg = message.lower().strip()
    
    # Handle greetings
    if any(greeting in msg for greeting in ['hello', 'hi', 'hey']):
        return f"Hello! I'm {config['agent_name']}, but I need an Anthropic API key to provide intelligent responses. Please set ANTHROPIC_API_KEY environment variable."
    
    # Handle time requests
    elif 'time' in msg:
        current_time = datetime.now().strftime("%H:%M:%S")
        return f"The current time is {current_time}."
    
    # Handle basic calculations
    elif any(op in message for op in ['+', '-', '*', '/', '=']):
        try:
            calculation = message.replace('x', '*').replace('X', '*').replace('=', '').strip()
            result = eval(calculation)
            return f"Calculation result: {calculation} = {result}"
        except:
            return "Sorry, I couldn't calculate that. Please check your expression."
    
    # Default fallback
    else:
        return f"I'm {config['agent_name']}, but I need an Anthropic API key to provide intelligent responses. Please set ANTHROPIC_API_KEY environment variable and restart me."

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to start the LLM-powered modular agent"""
    print(f"🤖 Starting {AGENT_CONFIG['agent_name']}")
    print(f"📝 Specialization: {AGENT_CONFIG['specialization']}")
    print(f"🎯 Domain: {AGENT_CONFIG['domain']}")
    print(f"🛠️ Capabilities: {', '.join(AGENT_CONFIG['expertise'])}")
    if AGENT_CONFIG['registry_url']:
        print(f"🌐 Registry: {AGENT_CONFIG['registry_url']}")
    
    # Check for Anthropic API key
    print(f"LLM PROVIDER: {AGENT_CONFIG['llm_provider']}")
    print(f"🧠 LLM Model: {AGENT_CONFIG['model']}")
    
    # Create the LLM-powered agent logic based on configuration
    agent_logic = create_llm_agent_logic(AGENT_CONFIG)
    
    print(f"Smithery api key: {os.getenv("SMITHERY_API_KEY")}")
    # Create and start the NANDA agent
    nanda = NANDA(
        agent_id=AGENT_CONFIG["agent_id"],
        agent_logic=agent_logic,
        port=PORT,
        registry_url=AGENT_CONFIG["registry_url"],
        mcp_registry_url=AGENT_CONFIG["mcp_registry_url"],
        public_url=AGENT_CONFIG["public_url"],
        enable_telemetry=True,
        smithery_api_key=os.getenv("SMITHERY_API_KEY")
    )
    
    print(f"🚀 Agent URL: http://localhost:{PORT}/a2a")
    print("💡 Try these messages:")
    print("   - 'Hello there'")
    print("   - 'Tell me about yourself'")
    print("   - 'What time is it?'")
    print("   - 'How can you help with Ubuntu?'")
    print("   - 'Explain Python virtual environments'")
    print("   - '5 + 3'")
    print("\n🛑 Press Ctrl+C to stop")
    
    # Start the agent
    nanda.start()

def create_custom_agent(agent_name, specialization, domain, expertise_list, port=6000, anthropic_api_key=None, registry_url=None):
    """
    Helper function to quickly create a custom LLM-powered agent with different config
    
    Example usage:
        create_custom_agent(
            agent_name="Data Scientist", 
            specialization="analytical and precise AI assistant",
            domain="data science",
            expertise_list=["data analysis", "statistics", "machine learning", "Python"],
            port=6001,
            anthropic_api_key="sk-ant-xxxxx"
        )
    """
    custom_config = AGENT_CONFIG.copy()
    custom_config.update({
        "agent_id": agent_name.lower().replace(" ", "-"),
        "agent_name": agent_name,
        "specialization": specialization,
        "domain": domain,
        "expertise": expertise_list,
        "registry_url": registry_url,
        "anthropic_api_key": anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"),
        "system_prompt": f"""You are {agent_name}, a {specialization} working in the domain of {domain}. 

You are part of the NANDA (Network of Autonomous Distributed Agents) system. You can communicate with other agents and help users with various tasks.

Your capabilities include:
{chr(10).join([f"- {expertise}" for expertise in expertise_list])}

Always be helpful, accurate, and concise in your responses. If you're unsure about something, say so honestly.

When someone asks about yourself, mention that you're part of the NANDA agent network and can communicate with other agents using the @agent_name syntax."""
    })
    
    agent_logic = create_llm_agent_logic(custom_config)
    
    nanda = NANDA(
        agent_id=custom_config["agent_id"],
        agent_logic=agent_logic,
        port=port,
        registry_url=custom_config["registry_url"],
        mcp_registry_url=custom_config["mcp_registry_url"],
        enable_telemetry=True,
        smithery_api_key=os.getenv("SMITHERY_API_KEY")
    )
    
    print(f"🤖 Starting custom LLM agent: {agent_name}")
    print(f"🚀 Agent URL: http://localhost:{port}/a2a")
    nanda.start()

if __name__ == "__main__":
    main()
