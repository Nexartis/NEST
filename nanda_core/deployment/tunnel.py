#!/usr/bin/env python3
"""
Tunnel Deployer - Deploy agents locally with public URL via tunneling

Uses ngrok to create public endpoints for local agents.
Perfect for hackathons, demos, and development.
"""

import os
import subprocess
import time
from typing import Optional
from .config import DeploymentConfig

try:
    from pyngrok import ngrok
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False


class TunnelDeployer:
    """
    Deploy agent locally with public tunnel.
    
    Creates a public URL for a local agent using ngrok.
    Useful for development, demos, and hackathons.
    """
    
    def __init__(self, auth_token: Optional[str] = None):
        """
        Initialize tunnel deployer.
        
        Args:
            auth_token: Optional ngrok auth token (can also use NGROK_AUTH_TOKEN env var)
        """
        if not NGROK_AVAILABLE:
            raise ImportError(
                "pyngrok is not installed. Install with: pip install pyngrok"
            )
        
        # Set auth token if provided
        self.auth_token = auth_token or os.getenv("NGROK_AUTH_TOKEN")
        if self.auth_token:
            ngrok.set_auth_token(self.auth_token)
            print("✅ Ngrok auth token configured")
        else:
            print("⚠️ No ngrok auth token provided. Using free tier with limitations.")
    
    def deploy_local(
        self,
        port: int = 6000,
        protocol: str = "http"
    ) -> str:
        """
        Create a tunnel to local port.
        
        Args:
            port: Local port where agent is running
            protocol: Protocol (http or tcp)
        
        Returns:
            Public URL for the tunnel
        """
        print(f"🚇 Creating {protocol} tunnel to localhost:{port}...")
        
        try:
            # Create tunnel
            tunnel = ngrok.connect(port, protocol)
            public_url = tunnel.public_url
            
            print(f"✅ Tunnel created: {public_url}")
            print(f"📡 Forwarding: {public_url} -> localhost:{port}")
            
            return public_url
            
        except Exception as e:
            print(f"❌ Failed to create tunnel: {e}")
            raise
    
    def close_tunnel(self, public_url: str):
        """
        Close a specific tunnel.
        
        Args:
            public_url: The public URL of the tunnel to close
        """
        try:
            ngrok.disconnect(public_url)
            print(f"🛑 Tunnel closed: {public_url}")
        except Exception as e:
            print(f"⚠️ Error closing tunnel: {e}")
    
    def close_all_tunnels(self):
        """Close all active tunnels."""
        try:
            ngrok.kill()
            print("🛑 All tunnels closed")
        except Exception as e:
            print(f"⚠️ Error closing tunnels: {e}")
    
    def get_active_tunnels(self) -> list:
        """
        Get list of active tunnels.
        
        Returns:
            List of active tunnel objects
        """
        try:
            tunnels = ngrok.get_tunnels()
            return tunnels
        except Exception as e:
            print(f"⚠️ Error getting tunnels: {e}")
            return []
    
    def deploy_with_config(self, config: DeploymentConfig) -> str:
        """
        Deploy using DeploymentConfig.
        
        Args:
            config: DeploymentConfig with provider="tunnel"
        
        Returns:
            Public URL
        """
        if config.provider != "tunnel":
            raise ValueError(f"Expected provider='tunnel', got '{config.provider}'")
        
        port = config.port
        protocol = config.extra_config.get("protocol", "http")
        
        return self.deploy_local(port=port, protocol=protocol)


# Convenience function
def create_tunnel(port: int = 6000, auth_token: Optional[str] = None) -> str:
    """
    Quick helper to create a tunnel.
    
    Args:
        port: Local port
        auth_token: Optional ngrok auth token
    
    Returns:
        Public URL
    
    Example:
        public_url = create_tunnel(6000)
        print(f"Agent accessible at: {public_url}")
    """
    deployer = TunnelDeployer(auth_token=auth_token)
    return deployer.deploy_local(port=port)