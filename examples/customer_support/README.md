# Customer Support Agent - LangGraph Example

Complex production-ready agent demonstrating NANDA + LangGraph integration.

## Features

- **Memory**: Maintains conversation history across messages
- **Multiple Tools**: CRM lookup, knowledge base search, ticket creation
- **Conditional Logic**: Automatic escalation based on sentiment
- **State Management**: Tracks conversation stage and customer info

## Setup

1. Install dependencies:
```bash
pip install langgraph langchain-anthropic anthropic
```

2. Set environment variables:
```bash
export ANTHROPIC_API_KEY="your-api-key"
export AGENT_ID="customer-support-agent"
export PORT="6000"
```

3. Run:
```bash
python deploy.py
```

## Test Messages
```bash
# Greeting
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"Hello, I need help","type":"text"},"role":"user","conversation_id":"test123"}'

# With customer ID
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"Hi, I am cust_001 and having billing issues","type":"text"},"role":"user","conversation_id":"test123"}'

# Negative sentiment (triggers escalation)
curl -X POST http://localhost:6000/a2a \
  -H "Content-Type: application/json" \
  -d '{"content":{"text":"This is terrible service!","type":"text"},"role":"user","conversation_id":"test123"}'
```

## Architecture
```
User Message
    ↓
greet_customer → analyze_inquiry → search_solution → check_escalation
                                                            ↓
                                                     [escalate or close]
                                                            ↓
                                                  escalate_to_human → END
                                                            ↓
                                                  close_conversation → END
```

## Mock Tools

- `lookup_customer_crm()`: Customer info (tier, status, history)
- `search_knowledge_base()`: KB articles for common issues
- `create_ticket()`: Support ticket creation
- `check_sentiment()`: Simple sentiment analysis

Replace with real APIs in production.