#!/usr/bin/env python3
"""
Adapters package - Framework adapters for different agent types
"""

from .simple import SimpleAdapter

__all__ = ['SimpleAdapter']

# LangGraph adapter will be imported when available
try:
    from .langgraph import LangGraphAdapter
    __all__.append('LangGraphAdapter')
except ImportError:
    pass