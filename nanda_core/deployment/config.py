#!/usr/bin/env python3
"""
Deployment Configuration

Configuration classes for different deployment scenarios.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DeploymentConfig:
    """
    Configuration for agent deployment.
    
    Contains all necessary information for deploying an agent
    to various platforms (AWS, local tunnel, etc.)
    """
    
    # Provider
    provider: str  # "aws", "tunnel", "manual"
    
    # Cloud credentials (for AWS, GCP, etc.)
    credentials: Optional[Dict[str, Any]] = None
    
    # Region/location
    region: Optional[str] = None
    
    # Instance configuration
    instance_type: Optional[str] = None
    
    # Environment variables to pass to deployed agent
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # Networking
    port: int = 6000
    
    # Additional provider-specific config
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration"""
        valid_providers = ["aws", "tunnel", "manual"]
        if self.provider not in valid_providers:
            raise ValueError(f"Invalid provider: {self.provider}. Must be one of {valid_providers}")
        
        if self.provider == "aws":
            if not self.credentials:
                raise ValueError("AWS deployment requires credentials")
            if not self.region:
                raise ValueError("AWS deployment requires region")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "provider": self.provider,
            "credentials": self.credentials,
            "region": self.region,
            "instance_type": self.instance_type,
            "env_vars": self.env_vars,
            "port": self.port,
            "extra_config": self.extra_config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentConfig':
        """Create config from dictionary"""
        return cls(**data)