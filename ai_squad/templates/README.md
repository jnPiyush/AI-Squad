# AI-Squad Templates

This directory contains customizable markdown templates used by AI-Squad agents to generate documentation.

## Available Templates

| Template | Agent | Output |
|----------|-------|--------|
| [prd.md](prd.md) | Product Manager | Product Requirements Document |
| [adr.md](adr.md) | Architect | Architecture Decision Record |
| [spec.md](spec.md) | Architect | Technical Specification |
| [ux.md](ux.md) | UX Designer | UX Design Document |
| [review.md](review.md) | Reviewer | Code Review Report |

## Customization

You can customize any template to match your organization's standards. Simply edit the markdown files in this directory.

### Template Variables

Templates use `{{variable}}` syntax for dynamic content. The following variables are available:

| Variable | Description | Used In |
|----------|-------------|---------|
| `{{issue_number}}` | GitHub issue number | All templates |
| `{{title}}` | Issue/PR title | All templates |
| `{{description}}` | Issue/PR description | All templates |
| `{{pr_number}}` | Pull request number | review.md |
| `{{files}}` | Changed files list | review.md |
| `{{codebase_context}}` | Relevant code context | prd.md |

### Example Customization

To add your company branding to the PRD template:

```markdown
# {{company_name}} Product Requirements Document (PRD)

**Issue:** #{{issue_number}}  
**Title:** {{title}}  
**Author:** AI-Squad Product Manager  
**Date:** [Date]  
**Department:** [Your Department]

---
```

### Best Practices

1. **Keep Variables**: Don't remove `{{variable}}` placeholders - they're replaced with actual values
2. **Maintain Structure**: Keep the general structure for consistent outputs
3. **Add Sections**: Feel free to add company-specific sections
4. **Remove Sections**: Remove sections that don't apply to your workflow
5. **Backup First**: Consider copying the original before making changes

## Fallback Behavior

If a template file is missing or unreadable, AI-Squad falls back to built-in default templates embedded in the code.

## Resetting Templates

To reset a template to defaults, simply delete the `.md` file. AI-Squad will use the embedded default template.

Or reinstall AI-Squad:
```bash
pip install --upgrade ai-squad
```

## Template Syntax

Templates support:
- Standard Markdown formatting
- Mermaid diagrams (in code blocks)
- ASCII art for wireframes
- Tables and checklists
- Code blocks with syntax highlighting

## Contributing

If you create improved templates, consider contributing them back to the project!
