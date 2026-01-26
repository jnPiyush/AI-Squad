# GitHub Models API Integration

## Overview

AI-Squad now supports GitHub Models API as a fallback AI provider, enabling real AI-powered agent collaboration without requiring the standalone Copilot CLI executable.

## Provider Chain

The AI provider fallback chain is now:

1. **GitHub Copilot SDK** (Primary) - Requires `copilot` CLI executable
2. **GitHub Models API** (Fallback #1) - Requires `GITHUB_TOKEN` or `gh` CLI auth
3. **OpenAI API** (Fallback #2) - Requires `OPENAI_API_KEY`
4. **Azure OpenAI** (Fallback #3) - Requires Azure credentials  
5. **Template-based** (Last Resort) - Always available

## Setup

### Option 1: Use GITHUB_TOKEN Environment Variable

```powershell
# Create token at https://github.com/settings/tokens
# Scopes needed: repo, read:org, read:user

$env:GITHUB_TOKEN = "ghp_your_token_here"

# Or set permanently:
[System.Environment]::SetEnvironmentVariable('GITHUB_TOKEN', 'ghp_your_token_here', 'User')
```

### Option 2: Use GitHub CLI Authentication

If you have GitHub CLI (`gh`) installed and authenticated, AI-Squad will automatically use its token:

```powershell
# Check if authenticated
gh auth status

# If not, authenticate
gh auth login
```

No additional setup needed - the GitHubModelsProvider will automatically retrieve the token from `gh auth token`.

## Configuration

Update `squad.yaml` to include `github_models` in the provider order:

```yaml
runtime:
  provider: copilot
  provider_order:
    - copilot
    - github_models  # ← ADD THIS
    - openai
    - azure_openai
```

## Features

### Model Name Mapping

GitHub Models API uses different model names than other providers. AI-Squad automatically maps common model names:

- `gpt-5.2` → `gpt-4o` (default)
- `gpt-4` → `gpt-4o`
- `gpt-3.5-turbo` → `gpt-4o-mini`  
- `claude-sonnet-4.5` → `gpt-4o`
- `claude-3-5-sonnet-20241022` → `gpt-4o`

### Token Limits

GitHub Models API free tier has a 16,000 token limit for requests. AI-Squad automatically:
- Limits max_tokens to 4,000 for output
- Falls back to templates if the request is too large

## Usage

Once configured, agents will automatically use GitHub Models API when Copilot CLI is unavailable:

```bash
# Standard commands work as normal
squad pm 123
squad joint-op 123 pm architect
squad mission -p "Create a task management API"
```

## Verification

Check which provider is active:

```python
from ai_squad.core.ai_provider import get_ai_provider

provider = get_ai_provider()
print("Available providers:", provider.get_available_providers())
print("Active provider:", provider.active_provider.provider_type.value)
```

Expected output:
```
Available providers: ['copilot', 'github_models']
Active provider: copilot
```

During execution, you'll see:
```
AI Provider available: copilot
AI Provider available: github_models
Copilot generation failed: [WinError 2] The system cannot find the file specified
AI generation successful using github_models
```

## Implementation Details

### GitHubModelsProvider Class

Location: `ai_squad/core/ai_provider.py`

Key methods:
- `_get_gh_token()` - Retrieves token from `gh auth token` if GITHUB_TOKEN not set
- `is_available()` - Validates token with GitHub API
- `generate()` - Makes POST request to `https://models.inference.ai.azure.com/chat/completions`

### Provider Chain Initialization

The `AIProviderChain` class initializes providers in order, checking availability with a 3-second timeout to prevent hangs.

### Auto-Fallback

When Copilot fails (e.g., executable not found), the chain automatically tries GitHub Models API without manual intervention.

## Troubleshooting

### Token Not Found

**Symptom:** GitHub Models provider not available

**Solutions:**
1. Set `GITHUB_TOKEN` environment variable
2. Run `gh auth login` if using GitHub CLI
3. Verify token: `gh auth token`

### 413 Token Limit Reached

**Symptom:** "Request body too large for gpt-4o model"

**Cause:** Issue/PR context exceeds 16,000 tokens

**Solutions:**
1. Use simpler issues with less context
2. System automatically falls back to templates
3. Consider using OpenAI API (higher limits) by setting `OPENAI_API_KEY`

### Model Not Supported

**Symptom:** "Unknown model: xyz"

**Solution:** AI-Squad includes model name mapping. If you encounter this, the model name needs to be added to the mapping in `GitHubModelsProvider.generate()`.

## Migration from Copilot SDK Only

Before this update, AI-Squad required the standalone Copilot CLI executable, which isn't always available. Now:

1. **No Changes Needed** - Existing Copilot SDK configurations continue to work
2. **Automatic Fallback** - If Copilot fails, GitHub Models API is tried automatically
3. **Same Commands** - All CLI commands work identically  
4. **Real AI** - No more template-only fallback when Copilot is unavailable

## Benefits

✅ **Real AI Collaboration** - Get actual AI-generated PRDs, ADRs, specs instead of templates  
✅ **No Executable Required** - Works with just GitHub token or `gh` CLI auth  
✅ **Automatic Fallback** - Seamless experience if Copilot unavailable  
✅ **Free Tier** - GitHub Models API is free for authenticated users  
✅ **Easy Setup** - One environment variable or use existing `gh` CLI auth

## Future Enhancements

Potential improvements:
- Context truncation to fit within token limits
- Streaming responses for real-time feedback
- Support for additional GitHub-hosted models
- Automatic model selection based on task complexity
- Rate limiting and retry logic

## Related Files

- `ai_squad/core/ai_provider.py` - Provider implementations
- `ai_squad/agents/base.py` - Agent AI calling logic  
- `squad.yaml` - Configuration with provider_order
- `setup.py` - Dependencies (includes `requests>=2.31.0`)

## Support

For issues or questions:
- Check GitHub token is valid: `gh auth token`
- Verify provider order in `squad.yaml`
- Enable debug logging: `export LOG_LEVEL=DEBUG` (or set in Python)
- Review logs for "AI Provider available: github_models"
