"""
Architect Agent

Creates Architecture Decision Records (ADRs) and technical specifications.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin

logger = logging.getLogger(__name__)


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
- **Self-Review & Quality Assurance**: Review your own ADRs and specifications for technical soundness, scalability considerations, and completeness

**Deliverables:**
1. ADR document at docs/adr/ADR-{{issue}}.md
2. Technical specification at docs/specs/SPEC-{{issue}}.md
3. Architecture document at docs/architecture/ARCH-{{issue}}.md
4. Architecture diagrams (Mermaid format)
5. API contracts and data models

**Skills Available:**
{skills}

**Process:**
1. **Research & Analysis Phase:**
   - Understand requirements from PRD (if available)
   - Research existing architecture patterns in codebase
   - Analyze existing ADRs in docs/adr/ for precedents
   - Review existing architecture documents in docs/architecture/
   - Study existing API contracts and data models
   - Evaluate current technology stack and constraints
   - Research industry best practices and patterns
   - Identify scalability and performance implications
   - Assess security requirements and compliance needs

2. **Design & Decision Making:**
   - Evaluate technical approaches and alternatives
   - Create ADR documenting decision with rationale
   - Design system architecture and component interactions

3. **Documentation & Specification:**
   - Write comprehensive architecture documentation
   - Write detailed technical specification
   - Include architecture diagrams (Mermaid format)
   - Define API contracts and data models
   - Ensure all deliverables are complete for Engineer

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
- **Before Submission**: Ensure ADR includes all alternatives considered, consequences are documented, and technical decisions align with existing architecture patterns
"""
    
    def get_output_path(self, issue_number: int) -> Path:
        """Get ADR output path"""
        return self.config.adr_dir / f"ADR-{issue_number}.md"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Architect agent logic"""
        
        # Get templates
        adr_template = self.templates.get_template("adr")
        spec_template = self.templates.get_template("spec")
        arch_template = self.templates.get_template("arch")
        
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
        
        # Generate ADR, Spec, and Architecture using AI
        if not self.sdk:
            raise RuntimeError(
                "AI provider required for architecture design. No AI providers available.\n"
                "Please configure at least one AI provider (see documentation)."
            )
        
        adr_content = self._generate_adr_with_sdk(issue, context, prd_content, adr_template)
        spec_content = self._generate_spec_with_sdk(issue, context, prd_content, spec_template)
        arch_content = self._generate_arch_with_sdk(issue, context, prd_content, arch_template)
        
        # Save outputs
        adr_path = self.get_output_path(issue["number"])
        spec_path = self.config.specs_dir / f"SPEC-{issue['number']}.md"
        arch_path = self.config.architecture_dir / f"ARCH-{issue['number']}.md"
        
        self._save_output(adr_content, adr_path)
        self._save_output(spec_content, spec_path)
        self._save_output(arch_content, arch_path)
        
        return {
            "success": True,
            "file_path": str(adr_path),
            "files": [str(adr_path), str(spec_path), str(arch_path)]
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
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if not result:
            raise RuntimeError("AI generation failed for ADR. All AI providers failed or timed out.")
        
        return result
    
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
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if not result:
            raise RuntimeError("AI generation failed for technical specification. All AI providers failed or timed out.")
        
        return result
    
    def _generate_arch_with_sdk(self, issue: Dict[str, Any], context: Dict[str, Any],
                                prd_content: str, template: str) -> str:
        """Generate architecture document using Copilot SDK"""
        
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Create a comprehensive architecture document for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**PRD (if available):**
{prd_content[:1000] if prd_content else 'No PRD available'}

**Codebase Context:**
{self._format_context(context)}

**Template to follow:**
{template}

Generate a complete architecture document including:
- System context and component diagrams
- Technology stack and design patterns
- Non-functional requirements analysis (scalability, performance, security)
- Deployment architecture and data flow
- Sequence diagrams for key scenarios
- Testing strategy and risk mitigation
"""
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if not result:
            raise RuntimeError("AI generation failed for architecture document. All AI providers failed or timed out.")
        
        return result
    
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
