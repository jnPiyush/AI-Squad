"""
Squad Mission Mode (Autonomous Orchestration)

Enables autonomous mission execution by accepting requirements as a "Squad Mission",
creating GitHub issues, and handing off to Captain for orchestration using Battle Plans.

Military Theme Integration:
- Requirements → Squad Mission
- Validation → Mission Analysis
- Issue Creation → Mission Assignment
- Handoff to Captain → Mission Deployment
- Captain uses Battle Plans and Convoys for orchestration
"""
import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def run_autonomous_workflow(
    requirements: str,
    plan_only: bool = False
) -> Dict[str, Any]:
    """
    Run Squad Mission workflow from requirements to completion.
    
    Military-Themed Workflow:
    1. Receive Squad Mission (requirements)
    2. Mission Analysis with PM (validate feature vs epic)
    3. Create Mission Brief in GitHub (epic/feature issue)
    4. Break down into Objectives (story issues)
    5. Deploy Mission to Captain for orchestration
    6. Captain coordinates using Battle Plans and Convoys
    
    Args:
        requirements: Squad Mission requirements (text)
        plan_only: If True, create mission brief without deploying to Captain
        
    Returns:
        Dict with mission deployment results
    """
    from ai_squad.core.config import Config
    from ai_squad.tools.github import GitHubTool
    from ai_squad.agents.product_manager import ProductManagerAgent
    from ai_squad.core.captain import Captain
    
    try:
        # Load configuration
        config = Config.load()
        github = GitHubTool(config)
        
        # Step 1: Mission Analysis with PM agent
        logger.info("📋 MISSION RECEIVED: Analyzing with PM")
        pm_agent = ProductManagerAgent(config)
        
        # PM validates and analyzes the mission
        mission_analysis = _analyze_mission_with_pm(
            pm_agent=pm_agent,
            mission_brief=requirements,
            config=config
        )
        
        if not mission_analysis["success"]:
            return {
                "success": False,
                "error": f"Mission analysis failed: {mission_analysis.get('error')}"
            }
        
        # Step 2: Create Mission Brief (GitHub issue)
        logger.info("📝 Creating Mission Brief in GitHub")
        mission_issue = _create_mission_brief(
            github=github,
            mission_analysis=mission_analysis,
            config=config
        )
        
        if not mission_issue:
            return {
                "success": False,
                "error": "Failed to create mission brief"
            }
        
        # Step 3: Create Mission Objectives (story issues)
        logger.info("🎯 Breaking down into Mission Objectives")
        objective_issues = _create_mission_objectives(
            github=github,
            mission_analysis=mission_analysis,
            mission_issue=mission_issue,
            config=config
        )
        
        result = {
            "success": True,
            "mission_brief": mission_issue,
            "objectives": objective_issues,
            "analysis_path": mission_analysis.get("file_path"),
            "mission_type": mission_analysis.get("mission_type")  # epic or feature
        }
        
        # Step 4: Deploy Mission to Captain (unless plan-only)
        if not plan_only:
            logger.info("🎖️ DEPLOYING MISSION TO CAPTAIN")
            captain = Captain(config)
            
            # Deploy mission brief to Captain for orchestration
            logger.info(f"⚔️ Deploying mission #{mission_issue} to Captain")
            
            # Captain coordinates using Battle Plans and Convoys
            deployment = _deploy_to_captain(
                captain=captain,
                issue_number=mission_issue,
                config=config
            )
            
            result["captain_deployment"] = deployment
        else:
            logger.info("📋 PLAN-ONLY: Mission brief created, awaiting manual deployment")
        
        return result
        
    except (RuntimeError, OSError, ValueError) as e:
        logger.error(f"Squad Mission failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _analyze_mission_with_pm(
    pm_agent: Any,
    mission_brief: str,
    config: Any
) -> Dict[str, Any]:
    """
    PM analyzes mission brief and determines:
    - Mission type (epic vs feature)
    - Objectives breakdown
    - Requirements structure
    
    Returns:
        Dict with mission analysis results
    """
    # Create a temporary "mission brief" document
    temp_brief_path = Path(config.workspace_root) / "docs" / "mission-brief.txt"
    temp_brief_path.parent.mkdir(parents=True, exist_ok=True)
    temp_brief_path.write_text(mission_brief, encoding="utf-8")
    
    logger.info("PM analyzing mission brief...")
    
    # Parse mission brief into structured format
    lines = mission_brief.strip().split("\n")
    title = lines[0] if lines else "Squad Mission"
    description = mission_brief
    
    # Determine mission type (epic = multiple major features, feature = single implementation)
    # Heuristic: if multiple "features" mentioned or >500 chars, treat as epic
    is_epic = (
        len(mission_brief) > 500 or
        mission_brief.lower().count("feature") > 1 or
        mission_brief.lower().count("system") > 0 or
        any(keyword in mission_brief.lower() for keyword in ["platform", "application", "app"])
    )
    
    mission_type = "epic" if is_epic else "feature"
    logger.info(f"Mission classified as: {mission_type.upper()}")
    
    # Extract objectives (user stories or features)
    objectives = []
    for line in lines:
        line = line.strip()
        if line.startswith("- ") or line.startswith("* ") or line.lower().startswith("as a"):
            objectives.append(line.lstrip("-*").strip())
    
    # If no explicit objectives, create one from the whole mission
    if not objectives:
        objectives = [title]
    
    return {
        "success": True,
        "title": title,
        "description": description,
        "mission_type": mission_type,
        "objectives": objectives,
        "file_path": str(temp_brief_path)
    }


def _create_mission_brief(
    github: Any,
    mission_analysis: Dict[str, Any],
    config: Any
) -> int:
    """
    Create mission brief issue in GitHub (epic or feature)
    
    Returns:
        Mission brief issue number
    """
    mission_type = mission_analysis.get("mission_type", "feature")
    title_prefix = "[MISSION: EPIC]" if mission_type == "epic" else "[MISSION: FEATURE]"
    
    title = f"{title_prefix} {mission_analysis['title']}"
    body = f"""# Squad Mission Brief

## Mission Type
**{mission_type.upper()}**

## Objective
{mission_analysis['description']}

## Mission Objectives
{chr(10).join([f'- {obj}' for obj in mission_analysis['objectives']])}

## Deployment Status
⏳ Awaiting Captain deployment

---
*Mission created by AI-Squad v{config.get('version', '0.4.0')}*
"""
    
    # Create issue
    labels = [f"type:{mission_type}", "ai-squad:mission", "status:pending-deployment"]
    issue = github.create_issue(
        title=title,
        body=body,
        labels=labels
    )
    
    logger.info(f"✅ Mission brief created: #{issue['number'] if issue else 'FAILED'}")
    return issue["number"] if issue else None


def _create_mission_objectives(
    github: Any,
    mission_analysis: Dict[str, Any],
    mission_issue: int,
    config: Any
) -> List[Dict[str, Any]]:
    """
    Create mission objective issues (stories) linked to mission brief
    
    Returns:
        List of objective issue dicts with 'number' key
    """
    objective_issues = []
    
    for idx, objective in enumerate(mission_analysis["objectives"], 1):
        title = f"[OBJECTIVE {idx}] {objective[:70]}"  # Truncate long titles
        body = f"""# Mission Objective

{objective}

## Mission Brief
Part of Mission #{mission_issue}

## Deployment
⏳ Awaiting Captain coordination

---
*Objective created by AI-Squad v{config.get('version', '0.4.0')}*
"""
        
        issue = github.create_issue(
            title=title,
            body=body,
            labels=["type:story", "ai-squad:objective", "status:pending-deployment"]
        )
        
        if issue:
            objective_issues.append(issue)
            
            # Add comment to mission brief linking this objective
            github.add_comment(
                mission_issue,
                f"🎯 Objective created: #{issue['number']} - {objective[:50]}..."
            )
    
    logger.info(f"✅ Created {len(objective_issues)} mission objectives")
    return objective_issues


def _deploy_to_captain(
    captain: Any,
    issue_number: int,
    config: Any
) -> Dict[str, Any]:
    """
    Deploy mission to Captain for orchestration using Battle Plans
    
    Captain will:
    - Analyze the issue
    - Select appropriate Battle Plan
    - Create Work Items
    - Organize into Convoys (parallel batches)
    - Dispatch to agents using handoffs
    - Monitor progress
    
    Returns:
        Dict with deployment status
    """
    logger.info(f"🎖️ Captain receiving mission #{issue_number}")
    
    try:
        # Captain's run method handles orchestration
        # It will analyze task, select battle plan, create convoys, etc.
        summary = asyncio.run(captain.run(issue_number))
        
        logger.info(f"✅ Captain deployment complete for #{issue_number}")
        return {
            "success": True,
            "issue_number": issue_number,
            "captain_summary": summary,
            "status": "deployed"
        }
        
    except Exception as e:
        logger.error(f"Captain deployment failed for #{issue_number}: {e}")
        return {
            "success": False,
            "issue_number": issue_number,
            "error": str(e),
            "status": "deployment-failed"
        }
