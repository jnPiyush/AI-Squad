"""
Product Manager Agent

Creates Product Requirements Documents (PRDs) and user stories.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin

logger = logging.getLogger(__name__)


class ProductManagerAgent(BaseAgent, ClarificationMixin):
    """Product Manager - Creates PRDs and breaks down epics"""
    
    def get_system_prompt(self) -> str:
        """Get PM system prompt"""
        skills = self._get_skills()
        
        # Try to load from external file first
        template = self._load_prompt_template("pm")
        if template:
            return self._render_prompt(template, skills=skills)
        
        # Fallback to embedded prompt
        return f"""You are an expert Product Manager on an AI development squad.

**Your Role:**
- Analyze user requests and business requirements
- Create comprehensive Product Requirements Documents (PRDs)
- Break down large epics into features and user stories
- Define acceptance criteria and success metrics
- Prioritize features based on business value

**Deliverables:**
1. PRD document at docs/prd/PRD-{{issue}}.md
2. GitHub issues for features and stories (if epic)
3. Clear acceptance criteria for each requirement

**Skills Available:**
{skills}

**Process:**
1. Read the issue description thoroughly
2. Research similar features in the codebase
3. Create PRD using the template
4. If epic: Break down into features and stories
5. Add acceptance criteria and success metrics
6. Save PRD and create issues (if needed)

**Template Structure:**
- Executive Summary
- Problem Statement
- Goals & Success Metrics
- User Stories
- Functional Requirements
- Non-Functional Requirements
- Dependencies & Assumptions
- Timeline & Milestones

**Best Practices:**
- Be specific and measurable
- Consider edge cases and error scenarios
- Include security and performance requirements
- Think about scalability and maintainability
- Reference existing patterns in codebase
"""
    
    def get_output_path(self, issue_number: int) -> Path:
        """Get PRD output path"""
        return self.config.prd_dir / f"PRD-{issue_number}.md"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PM agent logic"""
        
        # Get PRD template
        template = self.templates.get_template("prd")
        
        # Extract label names from label dicts
        labels = issue.get("labels", [])
        if labels and isinstance(labels[0], dict):
            label_names = [label.get("name", "") for label in labels]
        else:
            label_names = labels
        
        # Prepare template variables
        variables = {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
            "labels": ", ".join(label_names),
            "author": issue.get("user", {}).get("login", "Unknown"),
            "created_at": issue.get("created_at", ""),
            "codebase_context": self._format_context(context),
        }
        
        # Try SDK first, then fallback to template
        if self.sdk:
            prd_content = self._generate_with_sdk(issue, context, template)
        else:
            # Fallback: Use template with placeholders
            prd_content = self.templates.render(template, variables)
        
        # Save PRD
        output_path = self.get_output_path(issue["number"])
        self._save_output(prd_content, output_path)
        
        # If epic, create feature issues
        created_issues = []
        if "type:epic" in label_names:
            created_issues = self._create_feature_issues(issue, prd_content)
        
        return {
            "success": True,
            "file_path": str(output_path),
            "created_issues": created_issues
        }
    
    def _generate_with_sdk(self, issue: Dict[str, Any], context: Dict[str, Any], template: str) -> str:
        """Generate PRD using Copilot SDK"""
        
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Create a comprehensive PRD for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**Codebase Context:**
{self._format_context(context)}

**Template to follow:**
{template}

Generate a complete, production-ready PRD following the template structure.
"""
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if result:
            return result
        
        # Fallback to template if SDK call failed
        logger.warning("SDK call returned no result, falling back to template")
        return self.templates.render(template, {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
            "codebase_context": self._format_context(context),
        })
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format codebase context for prompt"""
        sections = []
        
        if context.get("similar_files"):
            sections.append("**Similar Files:**")
            for file in context["similar_files"][:5]:
                sections.append(f"- {file}")
        
        if context.get("related_issues"):
            sections.append("\n**Related Issues:**")
            for related in context["related_issues"][:3]:
                sections.append(f"- #{related['number']}: {related['title']}")
        
        return "\n".join(sections) if sections else "No specific context found"
    
    def _create_feature_issues(self, epic: Dict[str, Any], prd_content: str) -> list:
        """Create feature issues from epic PRD"""
        # TODO: Parse PRD and create feature issues
        # This would extract user stories/features from PRD and create GitHub issues
        return []
