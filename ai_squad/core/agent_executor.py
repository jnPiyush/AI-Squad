"""
Agent Executor

Executes agents using GitHub Copilot SDK.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

try:
    from github_copilot_sdk import CopilotSDK, Agent
except ImportError:
    # Fallback if SDK not available
    CopilotSDK = None
    Agent = None

from ai_squad.core.config import Config
from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.agents.architect import ArchitectAgent
from ai_squad.agents.engineer import EngineerAgent
from ai_squad.agents.ux_designer import UXDesignerAgent
from ai_squad.agents.reviewer import ReviewerAgent


class AgentExecutor:
    """Execute AI agents using Copilot SDK"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize agent executor
        
        Args:
            config_path: Path to squad.yaml (defaults to current directory)
        """
        self.config = Config.load(config_path)
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        
        # Initialize SDK if available
        self.sdk = None
        if CopilotSDK:
            self.sdk = CopilotSDK(token=self.github_token)
        
        # Agent mapping
        self.agents = {
            "pm": ProductManagerAgent(self.config, self.sdk),
            "architect": ArchitectAgent(self.config, self.sdk),
            "engineer": EngineerAgent(self.config, self.sdk),
            "ux": UXDesignerAgent(self.config, self.sdk),
            "reviewer": ReviewerAgent(self.config, self.sdk),
        }
    
    def execute(self, agent_type: str, issue_number: int) -> Dict[str, Any]:
        """
        Execute an agent for a given issue
        
        Args:
            agent_type: Type of agent ("pm", "architect", "engineer", "ux", "reviewer")
            issue_number: GitHub issue number
            
        Returns:
            Dict with execution result
        """
        if agent_type not in self.agents:
            return {
                "success": False,
                "error": f"Unknown agent type: {agent_type}"
            }
        
        agent = self.agents[agent_type]
        
        try:
            result = agent.execute(issue_number)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_agents(self) -> list:
        """Get list of available agents"""
        return list(self.agents.keys())
