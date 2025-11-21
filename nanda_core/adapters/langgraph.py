#!/usr/bin/env python3
"""
LangGraph Adapter - Adapter for LangGraph agents

Wraps LangGraph compiled graphs to work with NANDA's AgentInterface.
"""

from typing import Dict, Any, Optional, Callable
from ..interface import AgentInterface

try:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.graph import StateGraph
    from langchain_core.messages import HumanMessage, AIMessage as LCAIMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Create dummy classes for type hints
    class StateGraph:
        pass
    class CompiledStateGraph:
        pass


class LangGraphAdapter(AgentInterface):
    """
    Adapter for LangGraph agents.
    
    Handles state management and I/O translation between NANDA and LangGraph.
    """
    
    def __init__(
        self,
        graph: CompiledStateGraph,
        config: Optional[Dict] = None,
        response_extractor: Optional[Callable[[Dict], str]] = None
    ):
        """
        Initialize LangGraph adapter.
        
        Args:
            graph: CompiledStateGraph from LangGraph
            config: Optional config for graph execution
            response_extractor: Function to extract response string from graph output.
                              Default extracts last message content.
        """
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "LangGraph is not installed. Install with: pip install langgraph"
            )
        
        self.graph = graph
        self.config = config or {}
        self._conversations = {}  # In-memory state storage (TODO: make pluggable)
        
        # Set response extractor
        self.response_extractor = response_extractor or self._default_extractor
    
    def _default_extractor(self, result: Dict) -> str:
        """
        Default response extractor.
        
        Assumes graph output has 'messages' list with last message as response.
        
        Args:
            result: Graph execution result
        
        Returns:
            Extracted response string
        """
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            # Handle both Message objects and tuples
            if hasattr(last_message, 'content'):
                return last_message.content
            elif isinstance(last_message, tuple) and len(last_message) > 1:
                return last_message[1]
        
        # Fallback: stringify entire result
        return str(result)
    
    def process_message(self, message: str, context: Dict[str, Any]) -> str:
        """
        Process message through LangGraph (sync).
        
        Args:
            message: The message content
            context: Context with conversation_id
        
        Returns:
            Response string
        """
        conversation_id = context.get("conversation_id", "default")
        
        # Thread config for state persistence
        thread_config = {
            "configurable": {
                "thread_id": conversation_id
            }
        }
        # ADD THESE DEBUG LINES:
        print(f"DEBUG adapter: invoking with thread_id={conversation_id}")
        print(f"DEBUG adapter: graph has checkpointer={self.graph.checkpointer is not None}")

        
        # Merge with any additional config
        thread_config.update(self.config)
        
        # Invoke graph
        from langchain_core.messages import HumanMessage

        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},  # Use proper Message objects
            config=thread_config
        )
        
        # Extract and return response
        return self.response_extractor(result)
    
    async def process_message_async(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Process message through LangGraph (async).
        
        Uses ainvoke if available, falls back to sync invoke.
        
        Args:
            message: The message content
            context: Context with conversation_id
        
        Returns:
            Response string
        """
        conversation_id = context.get("conversation_id", "default")
        
        # Thread config for state persistence
        thread_config = {
            "configurable": {
                "thread_id": conversation_id
            }
        }
        
        # Merge with any additional config
        thread_config.update(self.config)
        
        # Check if graph supports async
        if hasattr(self.graph, 'ainvoke'):
            result = await self.graph.ainvoke(
                {"messages": [("user", message)]},
                config=thread_config
            )
        else:
            # Fallback to sync
            result = self.graph.invoke(
                {"messages": [("user", message)]},
                config=thread_config
            )
        
        # Extract and return response
        return self.response_extractor(result)
    
    def get_capabilities(self) -> list:
        """LangGraph adapters can define capabilities via metadata."""
        return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter metadata."""
        return {
            "adapter_type": "langgraph",
            "framework": "langgraph"
        }