# AI-Squad Agent Prompts

This directory contains customizable system prompts for each AI-Squad agent.

## Available Prompts

| Prompt | Agent | Description |
|--------|-------|-------------|
| [pm.md](pm.md) | Product Manager | Requirements gathering and PRD creation |
| [architect.md](architect.md) | Architect | Technical design and ADR creation |
| [engineer.md](engineer.md) | Engineer | Implementation and testing |
| [ux.md](ux.md) | UX Designer | User experience and accessibility |
| [reviewer.md](reviewer.md) | Reviewer | Code review and quality assurance |

## Customization

Edit any prompt file to customize agent behavior without modifying Python code.

### Template Variables

Prompts support `{variable}` syntax for dynamic values from `squad.yaml`:

| Variable | Source | Default |
|----------|--------|---------|
| `{skills}` | Agent's loaded skills | All skills |
| `{test_coverage_threshold}` | `quality.test_coverage_threshold` | 80 |
| `{test_pyramid_unit}` | `quality.test_pyramid.unit` | 70 |
| `{test_pyramid_integration}` | `quality.test_pyramid.integration` | 20 |
| `{test_pyramid_e2e}` | `quality.test_pyramid.e2e` | 10 |
| `{wcag_version}` | `accessibility.wcag_version` | 2.1 |
| `{wcag_level}` | `accessibility.wcag_level` | AA |
| `{contrast_ratio}` | `accessibility.contrast_ratio` | 4.5 |
| `{breakpoint_mobile}` | `design.breakpoints.mobile` | 320px-767px |
| `{breakpoint_tablet}` | `design.breakpoints.tablet` | 768px-1023px |
| `{breakpoint_desktop}` | `design.breakpoints.desktop` | 1024px+ |
| `{touch_target_min}` | `design.touch_target_min` | 44px |

### Example Customization

To add company-specific guidelines to the Engineer prompt:

```markdown
You are an expert Software Engineer on an AI development squad.

**Company Standards:**
- All code must pass SonarQube analysis
- Use Azure DevOps for CI/CD
- Follow {company_name} coding guidelines

**Your Role:**
...
```

## Fallback Behavior

If a prompt file is missing, the agent uses the embedded default prompt in Python code.

## Tips

1. **Keep Variables**: Don't remove `{variable}` placeholders
2. **Add Sections**: Add company-specific requirements
3. **Adjust Tone**: Modify language for your team's culture
4. **Extend Checklists**: Add project-specific review items
