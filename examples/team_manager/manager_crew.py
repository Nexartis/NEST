#!/usr/bin/env python3
"""
CrewAI Manager Crew - Coordinates Python and AWS specialists

Demonstrates CrewAI integration with NANDA for multi-agent coordination.
"""
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os
from dotenv import load_dotenv
load_dotenv()

# Choose LLM based on available API key
def get_llm():
    """Get available LLM"""
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.7)
    elif os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4", temperature=0.7)
    else:
        raise ValueError("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")

# Initialize LLM
llm = get_llm()

# Define Agents
manager = Agent(
    role='Project Manager',
    goal='Coordinate between Python and AWS specialists to complete user tasks',
    backstory="""You are an experienced project manager who understands both 
    software development and cloud infrastructure. You break down complex tasks 
    and delegate to the right specialists.""",
    llm=llm,
    verbose=True,
    allow_delegation=True
)

python_specialist = Agent(
    role='Python Developer',
    goal='Review, debug, and improve Python code',
    backstory="""You are a senior Python developer with 10+ years of experience. 
    You excel at code review, debugging, and suggesting best practices. You write 
    clean, maintainable code following PEP 8 standards.""",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

aws_specialist = Agent(
    role='AWS Cloud Architect',
    goal='Design and implement AWS infrastructure solutions',
    backstory="""You are an AWS certified solutions architect with deep knowledge 
    of EC2, S3, Lambda, and other AWS services. You design scalable, secure, and 
    cost-effective cloud architectures.""",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

def create_crew_for_task(user_request: str) -> Crew:
    """Create a crew dynamically based on user request"""
    
    # Analyze what specialists are needed
    needs_python = any(word in user_request.lower() 
                      for word in ['python', 'code', 'debug', 'review', 'script'])
    needs_aws = any(word in user_request.lower() 
                   for word in ['aws', 'deploy', 'ec2', 'cloud', 's3', 'lambda'])
    
    tasks = []
    agents = [manager]
    
    # Create tasks based on requirements
    if needs_python:
        python_task = Task(
            description=f"Handle the Python-related aspects of: {user_request}",
            agent=python_specialist,
            expected_output="Detailed Python code review, suggestions, or implementation"
        )
        tasks.append(python_task)
        agents.append(python_specialist)
    
    if needs_aws:
        aws_task = Task(
            description=f"Handle the AWS infrastructure aspects of: {user_request}",
            agent=aws_specialist,
            expected_output="AWS architecture recommendations and deployment strategy"
        )
        tasks.append(aws_task)
        agents.append(aws_specialist)
    
    # Manager's coordination task
    manager_task = Task(
        description=f"""Coordinate the team to complete: {user_request}
        
        Aggregate responses from specialists and provide a comprehensive answer.""",
        agent=manager,
        expected_output="Coordinated response incorporating all specialist inputs"
    )
    tasks.append(manager_task)
    
    # Create crew
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.hierarchical,  # Manager coordinates
        manager_llm=llm,
        verbose=True
    )
    
    return crew

def process_request(user_request: str) -> str:
    """Process user request through CrewAI crew"""
    try:
        crew = create_crew_for_task(user_request)
        result = crew.kickoff()
        return str(result)
    except Exception as e:
        return f"Error processing request: {str(e)}"