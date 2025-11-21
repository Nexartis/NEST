#!/usr/bin/env python3
"""
Customer Support Agent - Complex LangGraph example

Demonstrates a production-ready agent with:
- Memory (conversation history)
- Multiple tools (CRM, KB, tickets)
- Conditional logic (escalation)
- State management
"""

from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver

import os

# Import our mock tools
from tools import (
    lookup_customer_crm,
    search_knowledge_base,
    create_ticket,
    check_sentiment
)


# Define state schema
class AgentState(TypedDict):
    """State for customer support agent"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    customer_info: dict
    conversation_stage: str  # greeting, inquiry, resolving, escalating, closing
    escalation_needed: bool
    ticket_created: dict
    sentiment: str


def create_customer_support_agent(api_key: str = None):
    """
    Create a customer support LangGraph agent.
    
    Returns:
        Compiled LangGraph graph
    """
    
    # Initialize LLM
    llm = ChatAnthropic(
        api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307",
        temperature=0.7
    )
    
    # Node functions
    def greet_customer(state: AgentState) -> AgentState:
        """Initial greeting node"""
        last_message = state["messages"][-1]
        
        greeting = AIMessage(content=(
            "Hello! I'm your customer support assistant. "
            "I'm here to help you with any questions or issues. "
            "Could you please provide your customer ID, or tell me how I can assist you today?"
        ))
        
        return {
            **state,
            "messages": [greeting],
            "conversation_stage": "inquiry"
        }
    
    def analyze_inquiry(state: AgentState) -> AgentState:
        """Analyze customer inquiry using LLM"""
        last_message = state["messages"][-1]
        
        if isinstance(last_message, tuple):
            message_text = last_message[1]
        else:
            message_text = last_message.content
        
        # Use LLM to extract customer ID and analyze sentiment
        analysis_prompt = f"""Analyze this customer message:
    "{message_text}"

    Extract:
    1. Customer ID (format: cust_XXX) if mentioned
    2. Sentiment (positive/negative/neutral)

    Respond in JSON format:
    {{"customer_id": "cust_XXX or null", "sentiment": "positive/negative/neutral"}}"""

        analysis_response = llm.invoke([
            {"role": "user", "content": analysis_prompt}
        ]).content
        
        # Parse LLM response
        import json
        try:
            analysis = json.loads(analysis_response.strip().replace("```json", "").replace("```", ""))
            customer_id = analysis.get("customer_id")
            sentiment = analysis.get("sentiment", "neutral")
        except:
            # Fallback to simple extraction
            customer_id = None
            if "cust_" in message_text.lower():
                words = message_text.split()
                for word in words:
                    if word.startswith("cust_"):
                        customer_id = word
                        break
            sentiment = check_sentiment(message_text)
        
        # Lookup customer if ID found
        customer_info = {}
        if customer_id:
            result = lookup_customer_crm(customer_id)
            if result["success"]:
                customer_info = result["customer"]
        
        return {
            **state,
            "customer_info": customer_info,
            "sentiment": sentiment,
            "conversation_stage": "resolving"
        }

    def search_solution(state: AgentState) -> AgentState:
        """Search knowledge base and use LLM to generate helpful response"""
        last_message = state["messages"][-1]
        
        # Handle both tuple and Message object
        if isinstance(last_message, tuple):
            message_text = last_message[1]
        else:
            message_text = last_message.content
        
        # Get customer context
        customer_info = state.get("customer_info", {})
        customer_context = ""
        if customer_info:
            customer_context = f"\nCustomer Info: {customer_info.get('name', 'Unknown')} (Tier: {customer_info.get('tier', 'basic')})"
        
        # Search KB for relevant info
        kb_results = search_knowledge_base(message_text)
        
        # Build context for LLM
        kb_context = ""
        if kb_results["count"] > 0:
            kb_context = "\n\nRelevant KB Articles:\n"
            for result in kb_results["results"][:3]:  # Top 3 results
                kb_context += f"- {result['topic']}: {result['content']}\n"
        
        # Use LLM to generate intelligent response
        system_prompt = f"""You are a helpful customer support agent with access to conversation history.

IMPORTANT: You CAN see the full conversation history. Don't say you can't remember - refer back to previous messages when relevant.

Use the knowledge base articles to help answer the customer's question.
Be friendly, professional, and concise.{customer_context}

Available KB Articles:{kb_context if kb_context else " None found - offer to escalate"}

If you cannot find a solution in the KB, politely offer to escalate to a human agent."""

        # Build conversation history for LLM context
        conversation_messages = [{"role": "system", "content": system_prompt}]

        # Add previous messages from state (convert to LLM format)
        for msg in state["messages"][:-1]:  # All except current
            if isinstance(msg, tuple):
                conversation_messages.append({"role": "user", "content": msg[1]})
            elif isinstance(msg, AIMessage):
                conversation_messages.append({"role": "assistant", "content": msg.content})
            elif hasattr(msg, 'content'):
                conversation_messages.append({"role": "user", "content": msg.content})

        # Add current message
        conversation_messages.append({"role": "user", "content": message_text})

        response_text = llm.invoke(conversation_messages).content
        
        response = AIMessage(content=response_text)
        
        return {
            **state,
            "messages": [response]
        }
    
    def check_escalation(state: AgentState) -> AgentState:
        """Check if escalation is needed"""
        sentiment = state.get("sentiment", "neutral")
        
        # Escalate if negative sentiment or explicitly requested
        if sentiment == "negative" or state.get("escalation_needed", False):
            state["escalation_needed"] = True
            state["conversation_stage"] = "escalating"
        else:
            state["conversation_stage"] = "closing"
        
        return state
    
    def escalate_to_human(state: AgentState) -> AgentState:
        """Create ticket and use LLM to generate escalation message"""
        customer_info = state.get("customer_info", {})
        customer_id = customer_info.get("customer_id", "unknown")
        
        last_message = state["messages"][-2] if len(state["messages"]) > 1 else state["messages"][-1]
        if isinstance(last_message, tuple):
            message_text = last_message[1]
        else:
            message_text = last_message.content
        
        # Create ticket
        ticket_result = create_ticket(
            customer_id=customer_id,
            subject="Customer support escalation",
            description=f"Customer inquiry: {message_text}",
            priority="high" if state["sentiment"] == "negative" else "medium"
        )
        
        ticket_info = ticket_result["ticket"]
        
        # Use LLM to generate empathetic escalation message
        escalation_prompt = f"""Generate a professional escalation message for a customer.
        
    Context:
    - Customer sentiment: {state['sentiment']}
    - Ticket ID: {ticket_info['ticket_id']}
    - Customer email: {customer_info.get('email', 'your registered email')}

    Create a warm, empathetic message telling them their issue has been escalated and a human agent will contact them."""

        escalation_message = llm.invoke([
            {"role": "user", "content": escalation_prompt}
        ]).content
        
        response = AIMessage(content=escalation_message)
        
        return {
            **state,
            "ticket_created": ticket_info,
            "messages": [response],
            "conversation_stage": "closing"
        }
    
    def close_conversation(state: AgentState) -> AgentState:
        """Close conversation"""
        response = AIMessage(content=(
            "Thank you for contacting support! If you need further assistance, feel free to reach out anytime. "
            "Have a great day!"
        ))
        
        return {
            **state,
            "messages": [response]
        }
    
    # Build graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("greet", greet_customer)
    workflow.add_node("analyze", analyze_inquiry)
    workflow.add_node("search", search_solution)
    workflow.add_node("check", check_escalation)
    workflow.add_node("escalate", escalate_to_human)
    workflow.add_node("close", close_conversation)
    
    # Add edges
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "search")
    workflow.add_edge("search", END)
    # workflow.add_edge("search", "check")



    # Conditional routing from check
    def route_after_check(state: AgentState) -> str:
        if state.get("escalation_needed", False):
            return "escalate"
        else:
            return "close"

    workflow.add_conditional_edges(
        "check",
        route_after_check,
        {
            "escalate": "escalate",
            "close": "close"
        }
    )
    
    workflow.add_edge("escalate", END)
    workflow.add_edge("close", END)
    
    # Compile
    from langgraph.checkpoint.memory import MemorySaver

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# Custom response extractor for this agent
def extract_support_response(result: dict) -> str:
    """Extract response from customer support agent output."""
    print(f"DEBUG extract: result keys = {result.keys()}")
    print(f"DEBUG extract: messages = {result.get('messages', [])}")
    
    messages = result.get("messages", [])
    
    if messages:
        # Get last AI message
        for msg in reversed(messages):
            print(f"DEBUG: msg type = {type(msg)}, content preview")
            if isinstance(msg, AIMessage):
                return msg.content
    
    return "I apologize, but I encountered an error processing your request."