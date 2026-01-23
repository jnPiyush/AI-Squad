"""Core package initialization"""

from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.config import Config
from ai_squad.core.init_project import initialize_project

__all__ = ["AgentExecutor", "Config", "initialize_project"]
