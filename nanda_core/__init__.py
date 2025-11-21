#!/usr/bin/env python3
"""
NANDA Core - Agent coordination and deployment framework
"""

from .interface import AgentInterface
from .core.adapter import NANDA

__version__ = "1.0.0"
__all__ = ['NANDA', 'AgentInterface']