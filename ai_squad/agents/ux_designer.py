"""
UX Designer Agent

Creates wireframes, user flows, and design specifications.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin

logger = logging.getLogger(__name__)


class UXDesignerAgent(BaseAgent, ClarificationMixin):
    """UX Designer - Creates wireframes and user experience designs"""
    
    def get_system_prompt(self) -> str:
        """Get UX Designer system prompt"""
        skills = self._get_skills()
        
        # Try to load from external file first
        template = self._load_prompt_template("ux")
        if template:
            return self._render_prompt(template, skills=skills)
        
        # Fallback to embedded prompt (uses config values)
        wcag_ver = self.config.wcag_version
        wcag_lvl = self.config.wcag_level
        contrast = self.config.contrast_ratio
        breakpoints = self.config.breakpoints
        touch_min = self.config.touch_target_min
        
        return f"""You are an expert UX Designer on an AI development squad.

**Your Role:**
- Create user-centered designs
- Design wireframes and mockups
- Map user flows and journeys
- Ensure accessibility (WCAG {wcag_ver} {wcag_lvl})
- Design responsive interfaces

**Deliverables:**
1. UX design document at docs/ux/UX-{{issue}}.md
2. Wireframes (ASCII art or Mermaid diagrams)
3. User flow diagrams
4. Accessibility checklist
5. Responsive design specifications
6. Professional HTML click-through prototype at docs/ux/prototypes/prototype-{{issue}}.html

**Skills Available:**
{skills}

**Process:**
1. Understand user requirements from PRD
2. Research existing UI patterns in codebase
3. Create user flow diagrams
4. Design wireframes for key screens
5. Create professional HTML click-through prototype
6. Document interaction patterns
7. Ensure accessibility compliance
8. Specify responsive behavior

**Design Principles:**
- User-centered design
- Accessibility first (WCAG {wcag_ver} {wcag_lvl})
- Mobile-first responsive design
- Consistent with existing UI patterns
- Clear visual hierarchy
- Intuitive navigation
- Error prevention and clear feedback

**Wireframe Tools:**
- ASCII art for simple layouts
- Mermaid diagrams for flows
- Markdown tables for component specs

**HTML Prototype Requirements:**
- Self-contained single HTML file with inline CSS and JavaScript
- Professional, modern design with realistic styling
- Interactive elements (buttons, forms, navigation)
- Clickable navigation between key screens/states
- Responsive layout using CSS Grid/Flexbox
- Accessibility features (semantic HTML, ARIA labels, keyboard navigation)
- Smooth transitions and hover states
- Include placeholder content and sample data
- Browser-compatible (modern browsers)
- No external dependencies required

**Accessibility Requirements:**
- Proper heading hierarchy (h1-h6)
- Alt text for images
- ARIA labels where needed
- Keyboard navigation support
- Color contrast ratios ({contrast}:1 for text)
- Focus indicators
- Screen reader compatibility

**Responsive Design:**
- Mobile: {breakpoints.get('mobile', '320px-767px')}
- Tablet: {breakpoints.get('tablet', '768px-1023px')}
- Desktop: {breakpoints.get('desktop', '1024px+')}
- Flexible layouts (flexbox/grid)
- Touch-friendly targets ({touch_min} minimum)
"""
    
    def get_output_path(self, issue_number: int) -> Path:
        """Get UX design output path"""
        return self.config.ux_dir / f"UX-{issue_number}.md"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute UX Designer agent logic"""
        
        # Get UX template
        template = self.templates.get_template("ux")
        
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
            "ui_context": self._format_ui_context(context),
        }
        
        # Generate UX design
        if self.sdk:
            ux_content = self._generate_with_sdk(issue, context, prd_content, template)
            # Also generate HTML prototype
            html_prototype = self._generate_html_prototype(issue, context, prd_content)
        else:
            ux_content = self.templates.render(template, variables)
            html_prototype = None
        
        # Save outputs
        output_path = self.get_output_path(issue["number"])
        self._save_output(ux_content, output_path)
        
        files = [str(output_path)]
        
        # Save HTML prototype if generated
        if html_prototype:
            prototype_dir = self.config.ux_dir / "prototypes"
            prototype_path = prototype_dir / f"prototype-{issue['number']}.html"
            self._save_output(html_prototype, prototype_path)
            files.append(str(prototype_path))
        
        return {
            "success": True,
            "file_path": str(output_path),
            "files": files
        }
    
    def _generate_with_sdk(self, issue: Dict[str, Any], context: Dict[str, Any],
                          prd_content: str, template: str) -> str:
        """Generate UX design using Copilot SDK"""
        
        system_prompt = self.get_system_prompt()
        user_prompt = f"""Create a comprehensive UX design for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**PRD (if available):**
{prd_content[:1000] if prd_content else 'No PRD available'}

**Existing UI Patterns:**
{self._format_ui_context(context)}

**Template to follow:**
{template}

Generate a complete UX design with wireframes, user flows, and accessibility checklist.
Use ASCII art or Mermaid diagrams for wireframes.
"""
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if result:
            return result
        
        # Fallback to template
        logger.warning("SDK call returned no result for UX design, falling back to template")
        return self.templates.render(template, {
            "issue_number": issue["number"],
            "title": issue["title"],
            "description": issue["body"] or "",
        })
    
    def _generate_html_prototype(self, issue: Dict[str, Any], context: Dict[str, Any],
                                  prd_content: str) -> str:
        """Generate HTML click-through prototype using Copilot SDK"""
        # Context is currently unused for prototype generation; keep signature for future expansion
        _ = context
        
        system_prompt = """You are an expert UX Designer creating HTML prototypes.
Create self-contained, single-file HTML prototypes with:
- Inline CSS for professional, modern styling
- Interactive elements (buttons, forms, navigation)
- Responsive layout using CSS Grid/Flexbox
- Accessibility features (semantic HTML, ARIA labels)
- Smooth transitions and hover states"""
        
        user_prompt = f"""Create a professional HTML click-through prototype for:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**Requirements from PRD:**
{prd_content[:800] if prd_content else 'Create a general purpose prototype'}

Generate a complete, self-contained HTML file with:
1. Modern, professional styling (inline CSS)
2. Multiple screens/states accessible via navigation
3. Form elements and interactive components
4. Responsive design for mobile and desktop
5. WCAG 2.1 AA accessibility compliance
6. Sample/placeholder content

Output only the HTML code, starting with <!DOCTYPE html>.
"""
        
        result = self._call_sdk(system_prompt, user_prompt)
        return result
    
    def _format_ui_context(self, context: Dict[str, Any]) -> str:
        """Format UI context"""
        sections = []
        
        if context.get("ui_components"):
            sections.append("**Existing UI Components:**")
            for component in context["ui_components"][:5]:
                sections.append(f"- {component}")
        
        if context.get("design_patterns"):
            sections.append("\n**Design Patterns:**")
            for pattern in context["design_patterns"][:3]:
                sections.append(f"- {pattern}")
        
        return "\n".join(sections) if sections else "No existing UI patterns found"
