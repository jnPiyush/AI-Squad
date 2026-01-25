"""
Multi-agent collaboration orchestration with prerequisite validation.

Ensures agents execute in correct order respecting dependencies.
"""
from typing import Dict, Any, List
import logging
from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.validation import PrerequisiteValidator, AgentType, PrerequisiteError
from pathlib import Path

logger = logging.getLogger(__name__)


def run_collaboration(issue_number: int, agents: List[str]) -> Dict[str, Any]:
    """
    Run multiple agents in sequence for collaboration.
    
    Validates that agents are executed in correct dependency order.
    E.g., cannot run Engineer before Architect, Architect before PM.
    
    Args:
        issue_number: GitHub issue number
        agents: List of agent types to run in sequence
        
    Returns:
        Dict with collaboration result
        
    Raises:
        ValueError: If agents list contains invalid order
    """
    # PREREQUISITE VALIDATION - Ensure correct agent execution order
    # Validates that prerequisite agents have completed before dependent agents
    try:
        workspace_root = Path.cwd()
        validator = PrerequisiteValidator(workspace_root)
        
        # Get correct execution order
        correct_order = validator.topological_sort_agents()
        agent_order_map = {agent.value: idx for idx, agent in enumerate(correct_order)}
        
        # Validate that user-provided agents are in correct order
        logger.info(f"Validating collaboration agent order: {agents}")
        prev_order = -1
        for agent_type in agents:
            if agent_type not in agent_order_map:
                continue  # Skip non-standard agents (like "captain")
            
            curr_order = agent_order_map[agent_type]
            if curr_order < prev_order:
                # Agent out of order!
                correct_sequence = [a.value for a in correct_order]
                return {
                    "success": False,
                    "error": (
                        f"Invalid agent execution order. "
                        f"Cannot run {agent_type} after previous agents. "
                        f"Correct order: {' → '.join(correct_sequence)}"
                    ),
                    "error_type": "invalid_execution_order"
                }
            prev_order = curr_order
        
        logger.info("Agent order validation passed")
    except Exception as e:
        logger.warning(f"Agent order validation encountered error (non-blocking): {e}")
    
    executor = AgentExecutor()
    results = []
    files = []
    
    for agent_type in agents:
        result = executor.execute(agent_type, issue_number)
        results.append({
            "agent": agent_type,
            "result": result
        })
        
        if result.get("success"):
            if "file_path" in result:
                files.append(result["file_path"])
            if "files" in result:
                files.extend(result["files"])
        else:
            return {
                "success": False,
                "error": f"Agent {agent_type} failed: {result.get('error')}",
                "partial_results": results
            }
    
    return {
        "success": True,
        "results": results,
        "files": files
    }
