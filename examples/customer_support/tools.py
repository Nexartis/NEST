#!/usr/bin/env python3
"""
Mock tools for customer support agent

Simulates CRM lookup, ticket creation, and knowledge base search.
In production, these would connect to real APIs.
"""

from typing import Dict, Any, List
import time
import random


# Mock customer database
MOCK_CUSTOMERS = {
    "cust_001": {
        "customer_id": "cust_001",
        "name": "John Doe",
        "email": "john@example.com",
        "tier": "premium",
        "account_status": "active",
        "last_contact": "2024-01-15"
    },
    "cust_002": {
        "customer_id": "cust_002",
        "name": "Jane Smith",
        "email": "jane@example.com",
        "tier": "basic",
        "account_status": "active",
        "last_contact": "2024-01-10"
    }
}

# Mock knowledge base
MOCK_KB = {
    "reset_password": "To reset password: 1) Go to login page 2) Click 'Forgot Password' 3) Enter email 4) Check inbox for reset link",
    "billing_issue": "For billing issues: Check your account settings > Billing section. If issue persists, contact billing@example.com",
    "account_upgrade": "To upgrade account: Navigate to Settings > Subscription > Choose plan > Confirm payment",
    "technical_support": "For technical support: Check our status page at status.example.com. Contact support@example.com for urgent issues"
}

# Mock ticket storage
MOCK_TICKETS = {}
TICKET_COUNTER = 1000


def lookup_customer_crm(customer_id: str) -> Dict[str, Any]:
    """
    Look up customer information in CRM.
    
    Args:
        customer_id: Customer identifier
    
    Returns:
        Customer information dict
    """
    time.sleep(0.5)  # Simulate API latency
    
    customer = MOCK_CUSTOMERS.get(customer_id)
    
    if customer:
        return {
            "success": True,
            "customer": customer
        }
    else:
        return {
            "success": False,
            "error": "Customer not found"
        }


def search_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Search knowledge base for relevant articles.
    
    Args:
        query: Search query
    
    Returns:
        Search results
    """
    time.sleep(0.3)  # Simulate search latency
    
    query_lower = query.lower()
    
    # Simple keyword matching
    results = []
    for topic, content in MOCK_KB.items():
        if any(word in topic for word in query_lower.split()):
            results.append({
                "topic": topic,
                "content": content,
                "relevance": random.uniform(0.7, 1.0)
            })
    
    # Sort by relevance
    results.sort(key=lambda x: x["relevance"], reverse=True)
    
    return {
        "success": True,
        "query": query,
        "results": results,
        "count": len(results)
    }


def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Create a support ticket.
    
    Args:
        customer_id: Customer identifier
        subject: Ticket subject
        description: Ticket description
        priority: Priority level (low, medium, high, urgent)
    
    Returns:
        Created ticket information
    """
    global TICKET_COUNTER
    
    time.sleep(0.4)  # Simulate API latency
    
    ticket_id = f"TICKET-{TICKET_COUNTER}"
    TICKET_COUNTER += 1
    
    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "open",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "assigned_to": None
    }
    
    MOCK_TICKETS[ticket_id] = ticket
    
    return {
        "success": True,
        "ticket": ticket
    }


def check_sentiment(message: str) -> str:
    """
    Simple sentiment analysis.
    
    Args:
        message: Message text
    
    Returns:
        Sentiment: positive, negative, or neutral
    """
    negative_words = ["angry", "frustrated", "terrible", "worst", "hate", "bad", "awful"]
    positive_words = ["great", "excellent", "love", "best", "amazing", "wonderful"]
    
    message_lower = message.lower()
    
    neg_count = sum(1 for word in negative_words if word in message_lower)
    pos_count = sum(1 for word in positive_words if word in message_lower)
    
    if neg_count > pos_count:
        return "negative"
    elif pos_count > neg_count:
        return "positive"
    else:
        return "neutral"


# Tool descriptions for LangGraph
TOOL_DESCRIPTIONS = {
    "lookup_customer_crm": "Look up customer information including tier, account status, and contact history",
    "search_knowledge_base": "Search internal knowledge base for solutions to common issues",
    "create_ticket": "Create a support ticket for issues requiring escalation",
    "check_sentiment": "Analyze customer message sentiment to detect frustration or satisfaction"
}