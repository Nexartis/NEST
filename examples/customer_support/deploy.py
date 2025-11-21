#!/usr/bin/env python3
"""
Deploy customer support agent using NANDA

Shows how to integrate the complex LangGraph agent with NANDA.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from nanda_core.core.adapter import NANDA
from nanda_core.adapters import LangGraphAdapter
try:
    from .agent import create_customer_support_agent, extract_support_response
except ImportError:
    from agent import create_customer_support_agent, extract_support_response

from dotenv import load_dotenv
load_dotenv()

def main():
    """Deploy customer support agent"""
    
    print("=" * 60)
    print("Customer Support Agent - LangGraph Example")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    # Create LangGraph agent
    print("🔧 Building LangGraph customer support agent...")
    support_graph = create_customer_support_agent(api_key)
    print("✅ Agent graph compiled")
    
    # Wrap with LangGraph adapter
    print("🔧 Wrapping with LangGraphAdapter...")
    adapter = LangGraphAdapter(
        graph=support_graph,
        response_extractor=extract_support_response
    )
    print("✅ Adapter created")
    
    # Configuration
    agent_id = os.getenv("AGENT_ID", "customer-support-agent")
    port = int(os.getenv("PORT", "6000"))
    registry_url = os.getenv("REGISTRY_URL")
    public_url = os.getenv("PUBLIC_URL")
    
    # Create NANDA agent
    print("🔧 Creating NANDA agent...")
    nanda = NANDA(
        agent_id=agent_id,
        agent=adapter,
        port=port,
        registry_url=registry_url,
        public_url=public_url,
        enable_telemetry=True
    )
    
    print("\n" + "=" * 60)
    print("🤖 Customer Support Agent Ready!")
    print("=" * 60)
    print(f"Agent ID: {agent_id}")
    print(f"Port: {port}")
    print(f"URL: http://localhost:{port}/a2a")
    if registry_url:
        print(f"Registry: {registry_url}")
    
    print("\n💡 Try these messages:")
    print("   - 'Hello, I need help with my account cust_001'")
    print("   - 'I'm having billing issues'")
    print("   - 'How do I reset my password?'")
    print("   - 'This is terrible service!' (triggers escalation)")
    
    print("\n🛑 Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    # Start the agent
    nanda.start()


if __name__ == "__main__":
    main()