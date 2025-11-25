#!/usr/bin/env python3
"""
Deploy CrewAI Manager as NANDA Agent

Wraps CrewAI crew in NANDA for A2A communication.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from nanda_core import NANDA
from manager_crew import process_request

def crew_agent_logic(message: str, conversation_id: str) -> str:
    """
    Agent logic that uses CrewAI crew for processing
    """
    print(f"\n{'='*60}")
    print(f"📨 Received: {message}")
    print(f"🆔 Conversation: {conversation_id}")
    print(f"{'='*60}\n")
    
    # Process through CrewAI crew
    response = process_request(message)
    
    print(f"\n{'='*60}")
    print(f"✅ Crew Response Ready")
    print(f"{'='*60}\n")
    
    return response

if __name__ == "__main__":
    print("🚀 Starting CrewAI Manager Agent...")
    
    # Configuration
    AGENT_ID = os.getenv("AGENT_ID", "crewai-manager")
    PORT = int(os.getenv("PORT", "7000"))
    REGISTRY_URL = os.getenv("REGISTRY_URL")
    MCP_REGISTRY_URL = os.getenv("MCP_REGISTRY_URL")
    PUBLIC_URL = os.getenv("PUBLIC_URL")
    
    # Create NANDA agent with CrewAI logic
    nanda = NANDA(
        agent_id=AGENT_ID,
        agent_logic=crew_agent_logic,
        port=PORT,
        registry_url=REGISTRY_URL,
        mcp_registry_url=MCP_REGISTRY_URL,
        public_url=PUBLIC_URL,
        enable_telemetry=True,
        smithery_api_key=os.getenv("SMITHERY_API_KEY")
    )
    
    print(f"🎯 CrewAI Manager Agent: {AGENT_ID}")
    print(f"🌐 Port: {PORT}")
    print(f"📋 Registry: {REGISTRY_URL}")
    print(f"\n{'='*60}")
    print("CrewAI Crew Members:")
    print("  • Project Manager (coordinates)")
    print("  • Python Specialist")
    print("  • AWS Specialist")
    print(f"{'='*60}\n")
    
    nanda.start()