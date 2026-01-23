"""
Multi-agent collaboration orchestration
"""
from typing import Dict, Any, List
from ai_squad.core.agent_executor import AgentExecutor


def run_collaboration(issue_number: int, agents: List[str]) -> Dict[str, Any]:
    """
    Run multiple agents in sequence for collaboration
    
    Args:
        issue_number: GitHub issue number
        agents: List of agent types to run in sequence
        
    Returns:
        Dict with collaboration result
    """
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
