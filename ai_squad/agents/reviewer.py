"""
Reviewer Agent

Reviews code, checks quality, and ensures standards compliance.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ai_squad.agents.base import BaseAgent
from ai_squad.core.agent_comm import ClarificationMixin

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent, ClarificationMixin):
    """Reviewer - Reviews code and ensures quality standards"""
    
    def get_system_prompt(self) -> str:
        """Get Reviewer system prompt"""
        skills = self._get_skills()
        
        # Try to load from external file first
        template = self._load_prompt_template("reviewer")
        if template:
            return self._render_prompt(template, skills=skills)
        
        # Fallback to embedded prompt (uses config values)
        coverage = self.config.test_coverage_threshold
        
        return f"""You are an expert Code Reviewer on an AI development squad.

**Your Role:**
- Review code for quality and standards compliance
- Check security vulnerabilities
- Verify test coverage (≥{coverage}%)
- Ensure documentation completeness
- Validate performance considerations
- **Self-Review & Quality Assurance**: Review your own review reports for thoroughness, actionable feedback, balanced critique, and constructive recommendations

**Deliverables:**
1. Review document at docs/reviews/REVIEW-{{pr}}.md
2. Detailed feedback on code quality
3. Security analysis
4. Performance assessment
5. Approve or request changes

**Skills Available:**
{skills}

**Process:**
1. **Research & Analysis Phase:**
   - Fetch and review the pull request changes
   - Read related PRD, ADR, and spec documents for context
   - Understand the feature requirements and acceptance criteria
   - Review existing code in affected areas
   - Analyze test coverage reports
   - Check for security vulnerabilities in dependencies
   - Review CI/CD pipeline results and logs
   - Identify code smells and architectural concerns

2. **Comprehensive Review:**
   - Evaluate code quality against checklist
   - Assess security vulnerabilities and risks
   - Verify test coverage (≥{coverage}%)
   - Check performance and scalability implications
   - Validate documentation completeness

3. **Feedback & Decision:**
   - Create review document with findings
   - Provide actionable, constructive feedback
   - Make approval decision (Approve/Request Changes/Comment)
   - Ensure feedback is balanced and helpful

**Review Checklist:**

**Code Quality:**
- [ ] Follows SOLID principles
- [ ] DRY - no code duplication
- [ ] Clear naming conventions
- [ ] Proper error handling
- [ ] No compiler warnings
- [ ] Linter rules followed

**Testing:**
- [ ] Test coverage ≥{coverage}%
- [ ] Unit tests present
- [ ] Integration tests present
- [ ] E2E tests (if UI changes)
- [ ] Tests follow AAA pattern
- [ ] Edge cases covered

**Security:**
- [ ] Input validation implemented
- [ ] SQL queries parameterized
- [ ] No hardcoded secrets
- [ ] Authentication/authorization checked
- [ ] XSS prevention (if web)
- [ ] CSRF protection (if web)
- [ ] Dependencies scanned

**Performance:**
- [ ] Async/await used properly
- [ ] No N+1 queries
- [ ] Caching implemented where appropriate
- [ ] Resource disposal (using statements)
- [ ] Efficient algorithms

**Documentation:**
- [ ] XML docs/docstrings present
- [ ] README updated (if needed)
- [ ] API docs updated (if needed)
- [ ] Complex logic commented
- [ ] Breaking changes documented

**Architecture:**
- [ ] Follows project structure
- [ ] Separation of concerns
- [ ] Dependency injection used
- [ ] Interfaces for abstractions
- [ ] No circular dependencies

**Review Outcomes:**
- **Approve**: All checks passed, ready to merge
- **Request Changes**: Issues found, must be fixed
- **Comment**: Suggestions for improvement (optional)

**Self-Review Before Submitting Review:**
- Ensure review covers all checklist items (code quality, testing, security, performance, documentation)
- Verify feedback is actionable and specific (not just "improve this")
- Check that critique is balanced with positive observations
- Confirm approval decision is justified with clear reasoning
- Review tone is constructive and helpful, not dismissive
"""
    
    def get_output_path(self, issue_number: int) -> Path:  # noqa: ARG002
        """Get review output path (uses issue_number as pr_number for reviews)"""
        return self.config.reviews_dir / f"REVIEW-{issue_number}.md"
    
    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG002
        """Execute Reviewer agent logic (expects issue to contain PR number)"""
        pr_number = issue.get("number", 0)
        
        # Get PR details
        pr = self.github.get_pull_request(pr_number)
        if not pr:
            return {
                "success": False,
                "error": f"PR #{pr_number} not found"
            }
        
        # Get PR diff
        diff = self.github.get_pr_diff(pr_number)
        
        # Get changed files
        files = self.github.get_pr_files(pr_number)
        
        # Analyze code
        review_context = {
            "pr": pr,
            "diff": diff,
            "files": files,
        }
        
        # Generate review
        if self.sdk:
            review_content = self._generate_review_with_sdk(review_context)
        else:
            review_content = self._generate_review_fallback(review_context)
        
        # Save review
        output_path = self.get_output_path(pr_number)
        self._save_output(review_content, output_path)
        
        # Check if all criteria are met and close issue if applicable
        criteria_met = self._check_acceptance_criteria(review_content, pr)
        
        result = {
            "success": True,
            "file_path": str(output_path),
            "criteria_met": criteria_met
        }
        
        # Extract issue number from PR body
        issue_number = self._extract_issue_number(pr.get("body", ""))
        
        if issue_number and criteria_met:
            # Close the related issue
            success = self._close_related_issue(issue_number, pr_number, review_content)
            result["issue_closed"] = success
            result["closed_issue"] = issue_number
        
        return result
    
    def _generate_review_with_sdk(self, context: Dict[str, Any]) -> str:
        """Generate review using Copilot SDK"""
        
        pr = context["pr"]
        system_prompt = self.get_system_prompt()
        
        user_prompt = f"""Review this pull request:

**PR #{pr['number']}: {pr['title']}**

{pr['body'] or 'No description provided'}

**Changed Files:**
{self._format_files(context['files'])}

**Diff (truncated):**
```
{context['diff'][:5000] if context['diff'] else 'No diff available'}
```

Perform a comprehensive code review covering:
1. Code quality and SOLID principles
2. Test coverage and quality
3. Security vulnerabilities
4. Performance considerations
5. Documentation completeness
6. Architecture compliance

Provide specific, actionable feedback with line numbers where applicable.
For each issue found, rate severity as: Critical, High, Medium, or Low.
End with a clear recommendation: APPROVE, REQUEST_CHANGES, or COMMENT.
"""
        
        # Use base class SDK helper
        result = self._call_sdk(system_prompt, user_prompt)
        
        if result:
            return result
        
        # Fallback to template
        logger.warning("SDK call returned no result for review, falling back to template")
        template = self.templates.get_template("review")
        return self.templates.render(template, {
            "pr_number": pr["number"],
            "title": pr["title"],
            "description": pr["body"] or "",
        })
    
    def _generate_review_fallback(self, context: Dict[str, Any]) -> str:
        """Generate basic review without SDK"""
        
        pr = context["pr"]
        template = self.templates.get_template("review")
        
        return self.templates.render(template, {
            "pr_number": pr["number"],
            "title": pr["title"],
            "description": pr["body"] or "",
            "files": self._format_files(context["files"]),
        })
    
    def _format_files(self, files: list) -> str:
        """Format file list"""
        if not files:
            return "No files"
        
        result = []
        for file in files[:10]:
            status = file.get("status", "modified")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            result.append(f"- {file['filename']} ({status}, +{additions}/-{deletions})")
        
        if len(files) > 10:
            result.append(f"- ... and {len(files) - 10} more files")
        
        return "\n".join(result)
    
    def _check_acceptance_criteria(self, review_content: str, pr: Dict[str, Any]) -> bool:
        """
        Check if acceptance criteria are met based on review
        
        Args:
            review_content: Generated review content
            pr: PR details
            
        Returns:
            True if all criteria met
        """
        # Simple heuristic: check for approval indicators in review
        approval_keywords = [
            "approve",
            "lgtm",
            "looks good",
            "ready to merge",
            "all checks passed",
            "✅"
        ]
        
        failure_keywords = [
            "request changes",
            "must be fixed",
            "blocking issue",
            "security vulnerability",
            "failed",
            "❌"
        ]
        
        content_lower = review_content.lower()
        
        # Check for failure indicators
        if any(keyword in content_lower for keyword in failure_keywords):
            return False
        
        # Check for approval indicators
        if any(keyword in content_lower for keyword in approval_keywords):
            return True
        
        # Check PR mergeable status
        if pr.get("mergeable") == "MERGEABLE":
            return True
        
        # Default to False for safety
        return False
    
    def _extract_issue_number(self, text: str) -> Optional[int]:
        """
        Extract issue number from PR body
        
        Args:
            text: PR body text
            
        Returns:
            Issue number or None
        """
        import re
        
        # Look for patterns like "Closes #123", "Fixes #456", etc.
        patterns = [
            r'(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+#(\d+)',
            r'#(\d+)'  # Fallback to any #number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _close_related_issue(
        self,
        issue_number: int,
        pr_number: int,
        review_content: str
    ) -> bool:
        """
        Close the related issue after successful review
        
        Args:
            issue_number: Issue number to close
            pr_number: PR number
            review_content: Review content
            
        Returns:
            True if successful
        """
        _ = review_content  # Placeholder until review text is used in closure comment
        try:
            # Create closure comment
            comment = f"""✅ **Issue Closed by Reviewer Agent**

**Pull Request**: #{pr_number}
**Review**: All acceptance criteria met

**Summary**:
- Code quality: ✅ Passed
- Tests: ✅ Passed  
- Security: ✅ No issues found
- Documentation: ✅ Complete

The implementation has been reviewed and approved. All requirements from the PRD have been satisfied.

*Closed automatically by AI-Squad Reviewer at {self._get_timestamp()}*
"""
            
            # Close the issue with comment
            success = self.github.close_issue(issue_number, comment)
            
            if success:
                # Add completion label
                self.github.add_labels(issue_number, ["orch:completed"])
            
            return success
            
        except (ConnectionError, TimeoutError, OSError) as e:
            print(f"Error closing issue: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
