"""
Architect Agent

Creates Architecture Decision Records (ADRs) and technical specifications.
"""
from pathlib import Path
from typing import Dict, Any

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin


class ArchitectAgent(BaseAgent, ClarificationMixin):
    """Architect - Designs solutions and writes technical specs"""
    
    def get_system_prompt(self) -> str:
        """Get Architect system prompt"""
        skills = self._get_skills()
        
        # Try to load from external file first
        template = self._load_prompt_template("architect")
        if template:
            return self._render_prompt(template, skills=skills)
        
        # Fallback to embedded prompt
        return f"""You are an expert Software Architect on an AI development squad.

**Your Role:**
- Design scalable, maintainable solutions
- Create Architecture Decision Records (ADRs)
- Write detailed technical specifications
- Evaluate technology choices
- Plan system architecture and integrations

**Deliverables:**
1. ADR document at docs/adr/ADR-{{issue}}.md
2. Technical specification at docs/specs/SPEC-{{issue}}.md
3. Architecture diagrams (Mermaid format)
4. API contracts and data models

**Skills Available:**
{skills}

**Process:**
1. Understand requirements from PRD (if available)
2. Research existing architecture patterns in codebase
3. Evaluate technical approaches
4. Create ADR documenting decision
5. Write detailed technical specification
6. Include architecture diagrams
7. Define API contracts and data models

**ADR Structure:**
- Title
- Status (Proposed/Accepted/Deprecated)
- Context
- Decision
- Consequences (Positive/Negative)
- Alternatives Considered

**Spec Structure:**
- Overview
- Architecture Design
- Components & Responsibilities
- Data Models
- API Contracts
- Security Considerations
- Performance Requirements
- Testing Strategy

**Best Practices:**
- Follow SOLID principles
- Consider scalability and performance
- Document security implications
- Plan for monitoring and observability
- Use existing patterns where applicable
- Consider maintainability and technical debt
"""
    
    def get_output_path(self, issue_number: int) -> Path:
        """Get ADR output path"""
        return self.config.adr_dir / f"ADR-{issue_number}.md"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Architect agent logic"""
        
        # Get templates
        adr_template = self.templates.get_template("adr")
        spec_template = self.templates.get_template("spec")
        
        # Check if PRD exists
        prd_path = self.config.prd_dir / f"PRD-{issue['number']}.md"
        prd_content = ""
        if prd_path.exists():
            prd_content = prd_path.read_text(encoding="utf-8")
        
        # Prepare context
        variables = {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
            "prd_content": prd_content,
            "codebase_context": self._format_context(context),
        }
        
        # Generate ADR and Spec
        if self.sdk:
            adr_content = self._generate_adr_with_sdk(issue, context, prd_content, adr_template)
            spec_content = self._generate_spec_with_sdk(issue, context, prd_content, spec_template)
        else:
            adr_content = self.templates.render(adr_template, variables)
            spec_content = self.templates.render(spec_template, variables)
        
        # Save outputs
        adr_path = self.get_output_path(issue["number"])
        spec_path = self.config.specs_dir / f"SPEC-{issue['number']}.md"
        
        self._save_output(adr_content, adr_path)
        self._save_output(spec_content, spec_path)
        
        return {
            "success": True,
            "file_path": str(adr_path),
            "files": [str(adr_path), str(spec_path)]
        }
    
    def _generate_adr_with_sdk(self, issue: Dict[str, Any], context: Dict[str, Any], 
                               prd_content: str, template: str) -> str:
        """Generate ADR using Copilot SDK"""
        
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Create an Architecture Decision Record for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**PRD (if available):**
{prd_content[:1000] if prd_content else 'No PRD available'}

**Codebase Context:**
{self._format_context(context)}

**Template to follow:**
{template}

Generate a comprehensive ADR that documents the architectural decision and its rationale.
"""
        
        # Placeholder - actual SDK call would go here
        return self.templates.render(template, {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
        })
    
    def _generate_spec_with_sdk(self, issue: Dict[str, Any], context: Dict[str, Any],
                                prd_content: str, template: str) -> str:
        """Generate technical spec using Copilot SDK"""
        
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Create a detailed technical specification for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**PRD (if available):**
{prd_content[:1000] if prd_content else 'No PRD available'}

**Codebase Context:**
{self._format_context(context)}

**Template to follow:**
{template}

Generate a complete technical specification with architecture diagrams, API contracts, and data models.
"""
        
        # Placeholder - actual SDK call would go here
        return self.templates.render(template, {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
        })
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format codebase context"""
        sections = []
        
        if context.get("architecture_files"):
            sections.append("**Architecture Files:**")
            for file in context["architecture_files"][:5]:
                sections.append(f"- {file}")
        
        if context.get("similar_features"):
            sections.append("\n**Similar Features:**")
            for feature in context["similar_features"][:3]:
                sections.append(f"- {feature}")
        
        return "\n".join(sections) if sections else "No specific context found"
