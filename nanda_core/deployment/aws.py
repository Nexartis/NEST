#!/usr/bin/env python3
"""
AWS Deployer - Deploy agents to AWS EC2 using Terraform

Uses existing NEST Terraform scripts to deploy agents to AWS.
"""

import os
import subprocess
import json
import tempfile
import shutil
from typing import Dict, Any, Optional
from pathlib import Path
from .config import DeploymentConfig


class AWSDeployer:
    """
    Deploy agents to AWS EC2.
    
    Uses existing Terraform scripts from NEST for infrastructure deployment.
    """
    
    def __init__(self, terraform_dir: Optional[str] = None, credentials: Optional[Dict[str, str]] = None):
        """
        Initialize AWS deployer.
        
        Args:
            terraform_dir: Path to Terraform directory (required)
            credentials: AWS credentials
        """
        self.credentials = credentials
        
        # Find terraform directory (assumes we're in nanda_core/deployment)
        if terraform_dir is None:
            raise ValueError("terraform_dir is required. Provide path to your Terraform infrastructure.")
        
        self.terraform_dir = Path(terraform_dir)
        
        if not self.terraform_dir.exists():
            raise FileNotFoundError(f"Terraform directory not found at {self.terraform_dir}")
    
        print(f"📁 Terraform directory: {self.terraform_dir}")
    
    def deploy(
        self,
        agent_id: str,
        region: str,
        instance_type: str = "t3.micro",
        env_vars: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        Deploy agent to AWS EC2.
        
        Args:
            agent_id: Unique agent identifier
            region: AWS region (e.g., 'us-east-1')
            instance_type: EC2 instance type
            env_vars: Environment variables for the agent
            **kwargs: Additional deployment parameters
        
        Returns:
            Public endpoint URL of deployed agent
        """
        print(f"☁️ Deploying agent '{agent_id}' to AWS...")
        print(f"📍 Region: {region}")
        print(f"💻 Instance type: {instance_type}")
        
        try:
            # Set AWS credentials if provided
            if self.credentials:
                os.environ['AWS_ACCESS_KEY_ID'] = self.credentials.get('access_key_id', '')
                os.environ['AWS_SECRET_ACCESS_KEY'] = self.credentials.get('secret_access_key', '')
            
            # Create temporary tfvars file
            tfvars = self._create_tfvars(agent_id, region, instance_type, env_vars, **kwargs)
            tfvars_file = self._write_tfvars(tfvars)
            
            # Initialize Terraform
            print("🔧 Initializing Terraform...")
            self._run_terraform_command(["init"])
            
            # Plan deployment
            print("📋 Planning deployment...")
            self._run_terraform_command(["plan", f"-var-file={tfvars_file}"])
            
            # Apply deployment
            print("🚀 Deploying to AWS...")
            self._run_terraform_command(["apply", "-auto-approve", f"-var-file={tfvars_file}"])
            
            # Get output
            endpoint = self._get_terraform_output("agent_endpoint")
            
            print(f"✅ Agent deployed successfully!")
            print(f"🔗 Endpoint: {endpoint}")
            
            # Cleanup tfvars file
            os.remove(tfvars_file)
            
            return endpoint
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Deployment failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise
    
    def deploy_with_config(self, config: DeploymentConfig, agent_id: str) -> str:
        """
        Deploy using DeploymentConfig.
        
        Args:
            config: DeploymentConfig with provider="aws"
            agent_id: Agent identifier
        
        Returns:
            Public endpoint URL
        """
        if config.provider != "aws":
            raise ValueError(f"Expected provider='aws', got '{config.provider}'")
        
        credentials = config.credentials
        if credentials:
            self.credentials = credentials
        
        return self.deploy(
            agent_id=agent_id,
            region=config.region,
            instance_type=config.instance_type or "t3.micro",
            env_vars=config.env_vars,
            **config.extra_config
        )
    
    def destroy(self, agent_id: str):
        """
        Destroy deployed infrastructure.
        
        Args:
            agent_id: Agent identifier to destroy
        """
        print(f"🗑️ Destroying agent '{agent_id}' infrastructure...")
        
        try:
            self._run_terraform_command(["destroy", "-auto-approve"])
            print(f"✅ Infrastructure destroyed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Destroy failed: {e}")
            raise
    
    def _create_tfvars(
        self,
        agent_id: str,
        region: str,
        instance_type: str,
        env_vars: Optional[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Create Terraform variables dictionary."""
        tfvars = {
            "agent_id": agent_id,
            "region": region,
            "instance_type": instance_type,
            "environment_variables": env_vars or {}
        }
        
        # Add any additional config
        tfvars.update(kwargs)
        
        return tfvars
    
    def _write_tfvars(self, tfvars: Dict[str, Any]) -> str:
        """Write tfvars to temporary file."""
        fd, tfvars_file = tempfile.mkstemp(suffix=".tfvars.json", text=True)
        
        with os.fdopen(fd, 'w') as f:
            json.dump(tfvars, f, indent=2)
        
        print(f"📄 Created tfvars file: {tfvars_file}")
        return tfvars_file
    
    def _run_terraform_command(self, args: list):
        """Run terraform command."""
        cmd = ["terraform"] + args
        
        subprocess.run(
            cmd,
            cwd=self.terraform_dir,
            check=True,
            capture_output=False
        )
    
    def _get_terraform_output(self, output_name: str) -> str:
        """Get terraform output value."""
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=self.terraform_dir,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status of deployed agent.
        
        Args:
            agent_id: Agent identifier
        
        Returns:
            Status dictionary with endpoint, state, etc.
        """
        try:
            # Get all terraform outputs
            result = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=self.terraform_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            outputs = json.loads(result.stdout)
            
            return {
                "agent_id": agent_id,
                "status": "running",
                "outputs": outputs
            }
            
        except subprocess.CalledProcessError:
            return {
                "agent_id": agent_id,
                "status": "not_found"
            }
        except Exception as e:
            return {
                "agent_id": agent_id,
                "status": "error",
                "error": str(e)
            }