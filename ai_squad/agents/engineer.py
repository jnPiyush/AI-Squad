"""
Engineer Agent

Implements features with tests and documentation.
"""
import logging
from pathlib import Path
from typing import Dict, Any

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin

logger = logging.getLogger(__name__)


class EngineerAgent(BaseAgent, ClarificationMixin):
    """Engineer - Implements features with tests"""
    
    def get_system_prompt(self) -> str:
        """Get Engineer system prompt"""
        skills = self._get_skills()
        
        # Try to load from external file first
        template = self._load_prompt_template("engineer")
        if template:
            return self._render_prompt(template, skills=skills)
        
        # Fallback to embedded prompt (uses config values)
        coverage = self.config.test_coverage_threshold
        pyramid = self.config.test_pyramid
        
        return f"""You are an expert Software Engineer on an AI development squad.

**Your Role:**
- Implement features following specifications
- Write comprehensive tests (unit, integration, e2e)
- Document code with XML docs/docstrings
- Follow SOLID principles and design patterns
- Ensure ≥{coverage}% code coverage

**Deliverables:**
1. Implementation code with proper structure
2. Unit tests ({pyramid.get('unit', 70)}% of test suite)
3. Integration tests ({pyramid.get('integration', 20)}% of test suite)
4. E2E tests ({pyramid.get('e2e', 10)}% of test suite)
5. Code documentation (XML docs/docstrings)
6. Update relevant documentation

**Skills Available:**
{skills}

**Process:**
1. Read technical specification from Architect
2. Research existing code patterns
3. Implement feature following spec
4. Write tests (TDD approach preferred)
5. Document code
6. Run tests and ensure coverage ≥{coverage}%
7. Create pull request with detailed description

**Code Quality Standards:**
- SOLID principles
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- Test pyramid: {pyramid.get('unit', 70)}% unit, {pyramid.get('integration', 20)}% integration, {pyramid.get('e2e', 10)}% e2e
- No compiler warnings or linter errors
- Security: Input validation, SQL parameterization, no hardcoded secrets
- Performance: Async/await patterns, proper caching
- Error handling: Try-catch with specific exceptions

**Testing Requirements:**
- Arrange-Act-Assert pattern
- Test edge cases and error scenarios
- Mock external dependencies
- Test security constraints
- Measure code coverage (≥{coverage}%)

**Documentation:**
- XML docs for all public APIs (C#)
- Docstrings for all functions (Python)
- JSDoc for exported functions (JavaScript)
- Inline comments for complex logic
- Update README if needed
"""
    
    def get_output_path(self, issue_number: int) -> Path:
        """Engineers create multiple files - return primary file"""
        return Path.cwd() / "src"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Engineer agent logic"""
        
        # Get spec if available
        spec_path = self.config.specs_dir / f"SPEC-{issue['number']}.md"
        spec_content = ""
        if spec_path.exists():
            spec_content = spec_path.read_text(encoding="utf-8")
        
        # Prepare context
        implementation_context = {
            "issue": issue,
            "spec": spec_content,
            "codebase": context,
        }
        
        # Generate implementation
        if self.sdk:
            result = self._generate_implementation_with_sdk(implementation_context)
        else:
            result = self._generate_implementation_fallback(implementation_context)
        
        return result
    
    def _generate_implementation_with_sdk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate implementation using Copilot SDK"""
        
        issue = context["issue"]
        system_prompt = self.get_system_prompt()
        
        user_prompt = f"""Implement the feature for this issue:

**Issue #{issue['number']}: {issue['title']}**

{issue['body'] or 'No description provided'}

**Technical Specification:**
{context['spec'][:2000] if context['spec'] else 'No spec available - follow best practices'}

**Codebase Context:**
{self._format_context(context['codebase'])}

**Requirements:**
1. Create implementation files in appropriate directories
2. Write comprehensive tests (≥80% coverage)
3. Add XML docs/docstrings
4. Follow project coding standards
5. Handle errors gracefully
6. Consider security and performance

Generate the implementation files with complete code, tests, and documentation.
Provide the output as a structured response with file paths and content.
"""
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if result:
            # Parse SDK response and create files
            files_created = self._parse_and_create_files(result, issue['number'])
            return {
                "success": True,
                "files": files_created,
                "message": "Implementation generated with SDK",
                "sdk_response": result[:500] + "..." if len(result) > 500 else result
            }
        
        # Fallback if SDK call failed
        logger.warning("SDK call returned no result, falling back to guide generation")
        return self._generate_implementation_fallback(context)
    
    def _parse_and_create_files(self, sdk_response: str, issue_number: int) -> list:
        """
        Parse SDK response and create implementation files
        
        Args:
            sdk_response: Raw SDK response with code
            issue_number: Issue number for file naming
            
        Returns:
            List of created file paths
        """
        files_created = []
        
        # Save the raw SDK response as an implementation guide
        guide_path = Path.cwd() / "docs" / f"IMPL-{issue_number}.md"
        self._save_output(sdk_response, guide_path)
        files_created.append(str(guide_path))
        
        # TODO: Parse code blocks from SDK response and create actual files
        # This would involve:
        # 1. Extract ```python ... ``` or ```csharp ... ``` blocks
        # 2. Determine appropriate file paths from context
        # 3. Create the files with proper structure
        
        return files_created
    
    def _generate_implementation_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback implementation guidance"""
        
        issue = context["issue"]
        
        guidance = f"""# Implementation Guide for Issue #{issue['number']}

## Overview
{issue['title']}

## Specification
{context['spec'][:500] if context['spec'] else 'Follow best practices for this implementation'}

## Implementation Steps
1. Create feature files in appropriate directory structure
2. Implement core functionality
3. Add error handling and validation
4. Write unit tests
5. Write integration tests
6. Add documentation

## Code Quality Checklist
- [ ] SOLID principles applied
- [ ] Tests written (≥80% coverage)
- [ ] XML docs/docstrings added
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] Error handling added
- [ ] Performance optimized
- [ ] Security reviewed

## Next Steps
Run implementation manually following the guide above.
For automated implementation, configure GitHub Copilot SDK.
"""
        
        # Save guidance
        guide_path = Path.cwd() / "docs" / f"IMPL-GUIDE-{issue['number']}.md"
        self._save_output(guidance, guide_path)
        
        return {
            "success": True,
            "files": [str(guide_path)],
            "message": "Implementation guide created"
        }
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format codebase context"""
        sections = []
        
        if context.get("similar_code"):
            sections.append("**Similar Code Patterns:**")
            for code in context["similar_code"][:3]:
                sections.append(f"- {code}")
        
        if context.get("test_patterns"):
            sections.append("\n**Test Patterns:**")
            for pattern in context["test_patterns"][:3]:
                sections.append(f"- {pattern}")
        
        return "\n".join(sections) if sections else "No specific context found"
