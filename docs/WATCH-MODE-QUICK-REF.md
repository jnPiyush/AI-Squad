# Watch Mode Quick Reference

## 🚀 Quick Start

```bash
# Start watch mode
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
squad watch --repo owner/repo

# Keep it running in the background
# It will automatically trigger agents when labels change
```

## 🔄 Orchestration Flow

```
Issue Created
    ↓
PM runs: squad pm 123
    ↓ adds orch:pm-done
Watch detects → Triggers Architect
    ↓ adds orch:architect-done
Watch detects → Triggers Engineer
    ↓ adds orch:engineer-done
Watch detects → Triggers Reviewer
    ↓ closes issue
Done ✅
```

## 📋 Commands

| Command | Description |
|---------|-------------|
| `squad watch` | Start with repo from config |
| `squad watch --repo owner/repo` | Start with specific repo |
| `squad watch --interval 60` | Custom poll interval (10-300s) |
| `squad watch --help` | Show help |
| `Ctrl+C` | Stop watch mode |

## 🏷️ Label Triggers

| Label | Triggers | Agent Adds |
|-------|----------|------------|
| `orch:pm-done` | Architect | `orch:architect-done` |
| `orch:architect-done` | Engineer | `orch:engineer-done` |
| `orch:engineer-done` | Reviewer | Closes issue |

## 📊 Status Display

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃       AI-Squad Watch Mode        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Repository │ owner/repo          ┃
┃ Interval   │ 30s                 ┃
┃ Running    │ 00:05:23            ┃
┃ Events     │ 3 total, 0 queued   ┃
┃ Status     │ 🔄 Checking...      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## ⚙️ Configuration

`squad.yaml`:
```yaml
github:
  token: ${GITHUB_TOKEN}
  repo: owner/repo

watch:
  interval: 30
  enabled: true
```

## 🐛 Troubleshooting

| Error | Solution |
|-------|----------|
| "GitHub token not found" | `export GITHUB_TOKEN=ghp_xxx` |
| "Repository not configured" | Add `--repo owner/repo` or to config |
| "Invalid interval" | Use 10-300 seconds |
| Watch not detecting | Check label spelling: `orch:pm-done` |

## 📝 Manual Override

If you need to run agents manually while watch is running:

```bash
# Terminal 1: Watch mode running
squad watch --repo owner/repo

# Terminal 2: Manual execution (if needed)
squad ux 123    # Run UX Designer manually
squad pm 124    # Process another issue
```

## 🧪 Testing

```bash
# Run tests
pytest tests/test_watch.py -v

# Expected: 16/16 passing ✅
```

## 📚 Documentation

- Full Implementation: [WATCH-MODE-IMPLEMENTATION.md](WATCH-MODE-IMPLEMENTATION.md)
- Design Document: [AUTOMATION-DESIGN.md](AUTOMATION-DESIGN.md)
- Main README: [../README.md](../README.md)

---

**Version**: 0.2.0  
**Status**: ✅ Production Ready
