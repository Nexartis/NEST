#!/usr/bin/env python3
"""
LLM Provider Factory - Auto-detect provider from API key
"""

from typing import Optional
from .base import LLMProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from .gemini import GeminiProvider


def detect_provider(api_key: str) -> str:
    """
    Auto-detect LLM provider from API key format.
    
    Args:
        api_key: API key string
    
    Returns:
        Provider name: "anthropic", "openai", or "gemini"
    
    Raises:
        ValueError: If provider cannot be detected
    """
    if api_key.startswith("sk-ant-"):
        return "anthropic"
    elif api_key.startswith("sk-proj-") or api_key.startswith("sk-"):
        return "openai"
    elif api_key.startswith("AIza"):
        return "gemini"
    else:
        raise ValueError(
            f"Cannot detect LLM provider from API key format. "
            f"Please specify provider explicitly. "
            f"Supported: anthropic (sk-ant-*), openai (sk-*), gemini (AIza*)"
        )


def create_llm_provider(
    api_key: str,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> LLMProvider:
    """
    Create LLM provider instance.
    
    Args:
        api_key: API key
        provider: Provider name (auto-detected if None)
        model: Model name (uses default if None)
    
    Returns:
        LLMProvider instance
    
    Example:
        # Auto-detect from API key
        llm = create_llm_provider("sk-ant-abc123")
        
        # Explicit provider
        llm = create_llm_provider("sk-abc123", provider="openai", model="gpt-4-turbo")
    """
    # Auto-detect provider if not specified
    if provider is None:
        provider = detect_provider(api_key)
    
    provider = provider.lower()
    
    # Create provider instance
    if provider == "anthropic":
        model = model or "claude-3-haiku-20240307"
        return AnthropicProvider(api_key, model)
    
    elif provider == "openai":
        model = model or "gpt-4"
        return OpenAIProvider(api_key, model)
    
    elif provider == "gemini":
        model = model or "gemini-2.5-flash-lite"
        return GeminiProvider(api_key, model)
    
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: anthropic, openai, gemini"
        )