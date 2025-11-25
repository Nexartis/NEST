# CrewAI Manager Example - Multi-Agent Team Coordination

This example demonstrates how to build a coordinated team of AI agents using CrewAI within the NANDA framework.

## Architecture Overview

### Important: Team Coordination Architecture

**NANDA's A2A protocol is designed for peer-to-peer agent communication across networks, not for internal team coordination.** For building cohesive agent teams with hierarchical coordination, task delegation, and shared context, use frameworks like CrewAI, LangGraph, or AutoGen **within** a NANDA agent.
```
┌─────────────────────────────────────────────────────────────┐
│                     NANDA Agent Layer                        │
│                  (Network Communication)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         crewai-manager (Port 7000)                   │  │
│  │         Single NANDA Agent Endpoint                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              CrewAI Coordination Layer               │  │
│  │          (Internal Team Management)                   │  │
│  │                                                       │  │
│  │    ┌─────────────────────────────────────────┐      │  │
│  │    │      Manager Agent (Coordinator)        │      │  │
│  │    │  • Analyzes user requests               │      │  │
│  │    │  • Delegates to specialists             │      │  │
│  │    │  • Aggregates responses                 │      │  │
│  │    └─────────────────────────────────────────┘      │  │
│  │              │                    │                  │  │
│  │              ▼                    ▼                  │  │
│  │    ┌──────────────────┐  ┌──────────────────┐      │  │
│  │    │ Python Specialist│  │  AWS Specialist  │      │  │
│  │    │ • Code review    │  │ • Architecture   │      │  │
│  │    │ • Debugging      │  │ • Deployment     │      │  │
│  │    │ • Best practices │  │ • Cost analysis  │      │  │
│  │    └──────────────────┘  └──────────────────┘      │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
              External clients communicate
              via NANDA's A2A protocol
```

### Why This Architecture?

**NANDA A2A Protocol:**
- ✅ Best for: Inter-agent communication across networks
- ✅ Use case: Agent discovery, cross-organization coordination
- ✅ Example: Agent A (Company X) → Agent B (Company Y)

**CrewAI (or similar frameworks):**
- ✅ Best for: Internal team coordination within a single agent
- ✅ Use case: Task delegation, hierarchical workflows, shared memory
- ✅ Example: Manager → Python Dev → AWS Architect (same team)

**This Example Combines Both:**
- External communication: NANDA A2A
- Internal coordination: CrewAI hierarchical process

## Team Composition

### Manager Agent
- **Role**: Project Manager
- **Responsibility**: Coordinate between specialists, break down tasks
- **Capabilities**: 
  - Analyze user requests
  - Delegate to appropriate specialists
  - Aggregate and synthesize responses

### Python Specialist
- **Role**: Senior Python Developer
- **Responsibility**: Code review, debugging, implementation
- **Capabilities**:
  - Code quality analysis
  - PEP 8 compliance checking
  - Performance optimization suggestions
  - Bug identification and fixes

### AWS Specialist
- **Role**: Cloud Solutions Architect
- **Responsibility**: Infrastructure design and deployment
- **Capabilities**:
  - Architecture recommendations
  - Service selection (EC2, Lambda, S3, etc.)
  - Cost optimization
  - Security best practices

## How It Works

### Request Flow
```
1. External Request (via NANDA A2A)
   │
   ▼
2. NANDA Agent Receives Message
   │
   ▼
3. CrewAI Manager Analyzes Request
   │
   ├─ Needs Python help? → Delegate to Python Specialist
   │
   ├─ Needs AWS help? → Delegate to AWS Specialist
   │
   └─ Needs both? → Coordinate both specialists
   │
   ▼
4. Specialists Process Their Tasks (Parallel)
   │
   ▼
5. Manager Aggregates Responses
   │
   ▼
6. NANDA Returns Unified Response
```

### Example Interactions

**Simple Python Task:**
```
User: "Review this code: def add(a,b): return a+b"
→ Manager delegates to Python Specialist only
→ Returns: Code review with suggestions
```

**Simple AWS Task:**
```
User: "What's the best way to host a Flask app on AWS?"
→ Manager delegates to AWS Specialist only
→ Returns: Architecture recommendations
```

**Complex Multi-Specialist Task:**
```
User: "Review my Python microservice and design AWS deployment"
→ Manager delegates to BOTH specialists
→ Python Specialist: Reviews code quality, suggests improvements
→ AWS Specialist: Designs container-based deployment with ECS
→ Manager: Aggregates both responses into cohesive plan
```

## Setup

### Prerequisites
```bash

# Install CrewAI and LangChain
pip install crewai crewai-tools langchain-anthropic langchain-openai
```

### Configuration
```bash
# Set LLM API key (choose one)
export ANTHROPIC_API_KEY="sk-ant-..."
# OR
export OPENAI_API_KEY="sk-..."

# Optional: Registry for agent discovery
export REGISTRY_URL="http://localhost:6900"

# Optional: Custom port
export PORT="7000"
```

### Start the Agent
```bash
python deploy.py
```

Expected output:
```
🚀 Starting CrewAI Manager Agent...
🎯 CrewAI Manager Agent: crewai-manager
🌐 Port: 7000
📋 Registry: http://localhost:6900
============================================================
CrewAI Crew Members:
  • Project Manager (coordinates)
  • Python Specialist
  • AWS Specialist
============================================================
```

## Usage Examples

### Test 1: Python Code Review
```bash
curl -X POST http://localhost:7000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Review this Python code:\n\ndef calculate_total(items):\n    total = 0\n    for item in items:\n        total = total + item[\"price\"]\n    return total",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "review-001"
  }'
```

**Expected Response:**
- Code quality assessment
- PEP 8 compliance check
- Suggestions for improvement (e.g., use sum(), list comprehension)
- Edge case handling recommendations

### Test 2: AWS Architecture Question
```bash
curl -X POST http://localhost:7000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "I need to deploy a high-traffic Python API. What AWS architecture would you recommend?",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "aws-001"
  }'
```

**Expected Response:**
- Service recommendations (ALB, ECS/EKS, RDS)
- Scaling strategy
- Cost considerations
- Security best practices

### Test 3: Full Stack Coordination
```bash
curl -X POST http://localhost:7000/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "content": {
      "text": "Review my FastAPI application code and design a scalable AWS deployment with CI/CD",
      "type": "text"
    },
    "role": "user",
    "conversation_id": "fullstack-001"
  }'
```

**Expected Response:**
- Python code review from Python Specialist
- AWS architecture design from AWS Specialist
- Integrated deployment strategy coordinated by Manager
- CI/CD pipeline recommendations

## Key Features

### ✅ Hierarchical Coordination
- Manager acts as central coordinator
- Specialists focus on their domains
- Automatic task routing based on keywords

### ✅ Dynamic Task Creation
- CrewAI dynamically creates tasks based on user needs
- No hardcoded workflows
- Flexible specialist involvement

### ✅ Multi-LLM Support
- Works with Anthropic Claude
- Works with OpenAI GPT
- Auto-detects available API keys

### ✅ NANDA Integration
- Exposes team as single A2A endpoint
- Compatible with NANDA registry
- Can communicate with other NANDA agents

### ✅ Verbose Logging
- See agent reasoning in real-time
- Track task delegation
- Debug coordination flow

## Extending the Example
