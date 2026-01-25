"""
Multi-agent collaboration orchestration with iterative dialogue.

Supports two modes:
1. Sequential: Agents execute in order (legacy mode)
2. Iterative: Agents engage in back-and-forth dialogue with feedback loops

Ensures agents execute in correct order respecting dependencies.
"""
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging
import uuid
from datetime import datetime
from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.validation import PrerequisiteValidator
from ai_squad.core.signal import SignalManager, MessagePriority
from ai_squad.core.handoff import HandoffManager, HandoffReason
from ai_squad.core.config import Config
from pathlib import Path

logger = logging.getLogger(__name__)


class CollaborationMode(str, Enum):
    """Collaboration execution modes"""
    SEQUENTIAL = "sequential"  # Run agents in sequence (no dialogue)
    ITERATIVE = "iterative"    # Agents iterate with feedback loops


def run_collaboration(
    issue_number: int, 
    agents: List[str],
    mode: CollaborationMode = CollaborationMode.ITERATIVE,
    max_iterations: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run multiple agents in collaboration with optional iterative dialogue.
    
    Sequential Mode (for 2+ agents):
    - Validates agents are executed in correct dependency order
    - Each agent runs once in sequence
    - E.g., cannot run Engineer before Architect, Architect before PM
    
    Iterative Mode (default - for 2 agents):
    - Agents engage in back-and-forth dialogue
    - Agent A produces output → Agent B reviews and provides feedback
    - Agent A iterates based on feedback → Repeat until approval or max iterations
    - Uses Signal system for feedback and Handoff system for work transfer
    
    Args:
        issue_number: GitHub issue number
        agents: List of agent types (exactly 2 for iterative mode, 2+ for sequential)
        mode: Collaboration mode (default: iterative)
        max_iterations: Maximum iteration rounds (default: from config or 3)
        
    Returns:
        Dict with collaboration result including:
        - success: bool
        - mode: str (sequential or iterative)
        - results: List of agent results
        - files: List of output files
        - iterations: int (for iterative mode)
        - conversation_thread: str (for iterative mode)
        
    Raises:
        ValueError: If agents list is invalid for selected mode
    """
    # Load max_iterations from config if not specified
    if max_iterations is None:
        config = Config.load()
        max_iterations = config.get("collaboration", {}).get("max_iterations", 3)
    
    if mode == CollaborationMode.ITERATIVE:
        return _run_iterative_collaboration(issue_number, agents, max_iterations)
    else:
        return _run_sequential_collaboration(issue_number, agents)


def _run_sequential_collaboration(issue_number: int, agents: List[str]) -> Dict[str, Any]:
    """
    Run agents in sequential order (legacy mode).
    
    Each agent runs once in dependency order.
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
        logger.info("Validating collaboration agent order: %s", agents)
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
    except (RuntimeError, OSError, ValueError) as e:
        logger.warning("Agent order validation encountered error (non-blocking): %s", e)
    
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
        "mode": "sequential",
        "results": results,
        "files": files
    }


def _run_iterative_collaboration(
    issue_number: int, 
    agents: List[str],
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Run agents in iterative dialogue mode with feedback loops.
    
    Flow:
    1. Agent A (primary) produces initial output
    2. Agent B (reviewer) reviews and sends feedback via Signal
    3. Agent A receives feedback and iterates
    4. Repeat until:
       - Agent B approves (feedback is positive)
       - Max iterations reached
       - Error occurs
    
    Args:
        issue_number: GitHub issue number
        agents: Exactly 2 agents [primary, reviewer]
        max_iterations: Maximum iteration rounds (default: 3)
        
    Returns:
        Dict with collaboration result including conversation history
    """
    # Validate exactly 2 agents
    if len(agents) != 2:
        return {
            "success": False,
            "error": "Iterative mode requires exactly 2 agents (e.g., pm architect)",
            "error_type": "invalid_agent_count"
        }
    
    primary_agent, reviewer_agent = agents[0], agents[1]
    workspace_root = Path.cwd()
    
    # Initialize communication systems
    signal_manager = SignalManager(workspace_root)
    # Note: HandoffManager requires additional dependencies, we'll use signals for now
    
    # Create conversation thread
    thread_id = f"collab-{issue_number}-{uuid.uuid4().hex[:8]}"
    conversation_history = []
    
    logger.info(
        "Starting iterative collaboration: %s ↔ %s (thread: %s, max_iterations: %d)",
        primary_agent, reviewer_agent, thread_id, max_iterations
    )
    
    executor = AgentExecutor()
    files = []
    iteration = 0
    approved = False
    
    # Initial execution by primary agent
    logger.info("[Iteration %d] %s: Initial execution", iteration, primary_agent)
    primary_result = executor.execute(primary_agent, issue_number)
    
    if not primary_result.get("success"):
        return {
            "success": False,
            "mode": "iterative",
            "error": f"{primary_agent} failed: {primary_result.get('error')}",
            "iterations": iteration,
            "thread_id": thread_id
        }
    
    conversation_history.append({
        "iteration": iteration,
        "agent": primary_agent,
        "action": "initial_output",
        "result": primary_result,
        "timestamp": datetime.now().isoformat()
    })
    
    if primary_result.get("file_path"):
        files.append(primary_result["file_path"])
    if primary_result.get("files"):
        files.extend(primary_result["files"])
    
    # Iterative feedback loop
    for iteration in range(1, max_iterations + 1):
        logger.info("[Iteration %d] %s: Reviewing output", iteration, reviewer_agent)
        
        # Reviewer agent provides feedback
        feedback_prompt = (
            f"Review the {primary_agent}'s output for issue #{issue_number}. "
            f"Provide constructive feedback or approve if satisfactory. "
            f"Output files: {', '.join(files)}"
        )
        
        # Execute reviewer with context about primary agent's output
        reviewer_result = executor.execute(
            reviewer_agent, 
            issue_number,
            # TODO: Pass primary_result as context when executor supports it
        )
        
        if not reviewer_result.get("success"):
            logger.warning("%s review failed: %s", reviewer_agent, reviewer_result.get("error"))
            # Continue with partial feedback
            feedback = {
                "approved": False,
                "comments": f"Review incomplete: {reviewer_result.get('error')}",
                "severity": "warning"
            }
        else:
            # Parse reviewer output for feedback
            feedback = _parse_feedback(reviewer_result)
        
        conversation_history.append({
            "iteration": iteration,
            "agent": reviewer_agent,
            "action": "review",
            "feedback": feedback,
            "result": reviewer_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Send feedback via Signal
        signal_manager.send_message(
            sender=reviewer_agent,
            recipient=primary_agent,
            subject=f"Feedback on Issue #{issue_number} - Iteration {iteration}",
            body=feedback.get("comments", ""),
            priority=MessagePriority.HIGH if not feedback.get("approved") else MessagePriority.NORMAL,
            work_item_id=f"issue-{issue_number}",
            thread_id=thread_id,
            metadata={
                "iteration": iteration,
                "approved": feedback.get("approved", False),
                "severity": feedback.get("severity", "info")
            }
        )
        
        # Check if approved
        if feedback.get("approved"):
            logger.info("[Iteration %d] %s approved! Collaboration complete.", iteration, reviewer_agent)
            approved = True
            break
        
        # Check if max iterations reached
        if iteration >= max_iterations:
            logger.warning(
                "[Iteration %d] Max iterations reached without approval. Ending collaboration.",
                iteration
            )
            break
        
        # Primary agent iterates based on feedback
        logger.info("[Iteration %d] %s: Iterating based on feedback", iteration, primary_agent)
        
        # Execute primary agent again with feedback context
        primary_result = executor.execute(
            primary_agent,
            issue_number,
            # TODO: Pass feedback as context when executor supports it
        )
        
        if not primary_result.get("success"):
            logger.error("%s iteration failed: %s", primary_agent, primary_result.get("error"))
            # Add failed iteration to conversation history
            conversation_history.append({
                "iteration": iteration,
                "agent": primary_agent,
                "action": "iteration_failed",
                "result": primary_result,
                "timestamp": datetime.now().isoformat()
            })
            return {
                "success": False,
                "mode": "iterative",
                "error": f"{primary_agent} iteration {iteration} failed: {primary_result.get('error')}",
                "iterations": iteration,
                "thread_id": thread_id,
                "conversation": conversation_history
            }
        
        conversation_history.append({
            "iteration": iteration,
            "agent": primary_agent,
            "action": "iteration",
            "result": primary_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update files
        if primary_result.get("file_path") and primary_result["file_path"] not in files:
            files.append(primary_result["file_path"])
        if primary_result.get("files"):
            for f in primary_result["files"]:
                if f not in files:
                    files.append(f)
    
    # Final result
    return {
        "success": True,
        "mode": "iterative",
        "approved": approved,
        "iterations": iteration,
        "thread_id": thread_id,
        "conversation": conversation_history,
        "files": files,
        "participants": {
            "primary": primary_agent,
            "reviewer": reviewer_agent
        }
    }


def _parse_feedback(reviewer_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse reviewer agent's output to extract feedback.
    
    Looks for approval indicators and extracts comments.
    
    Args:
        reviewer_result: Agent execution result
        
    Returns:
        Dict with:
        - approved: bool
        - comments: str
        - severity: str (info, warning, critical)
    """
    output = reviewer_result.get("output", "")
    
    # Check for approval keywords
    approval_keywords = ["approved", "looks good", "lgtm", "acceptable", "satisfactory"]
    rejection_keywords = ["needs work", "revise", "fix", "issue", "problem", "concern"]
    
    output_lower = output.lower()
    
    approved = any(keyword in output_lower for keyword in approval_keywords)
    has_concerns = any(keyword in output_lower for keyword in rejection_keywords)
    
    # If both approval and concerns, prioritize concerns
    if has_concerns:
        approved = False
    
    # Determine severity
    severity = "info"
    if "critical" in output_lower or "blocking" in output_lower:
        severity = "critical"
    elif "warning" in output_lower or "concern" in output_lower:
        severity = "warning"
    
    return {
        "approved": approved,
        "comments": output[:500] if output else "No feedback provided",  # Limit length
        "severity": severity
    }


# Backward compatibility alias
def run_sequential_collaboration(issue_number: int, agents: List[str]) -> Dict[str, Any]:
    """Legacy function for sequential collaboration."""
    return run_collaboration(issue_number, agents, mode=CollaborationMode.SEQUENTIAL)


def run_iterative_collaboration(
    issue_number: int, 
    agents: List[str],
    max_iterations: int = 3
) -> Dict[str, Any]:
    """Convenience function for iterative collaboration."""
    return run_collaboration(issue_number, agents, mode=CollaborationMode.ITERATIVE, max_iterations=max_iterations)
