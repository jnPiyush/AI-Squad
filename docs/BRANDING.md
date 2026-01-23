# AI-Squad Branding & Logo

## Brand Identity

**Name**: AI-Squad  
**Tagline**: Your AI Development Squad, One Command Away  
**Mission**: Automate software development with specialized AI agents

---

## Color Palette

### Primary Colors
- **Squad Blue**: `#0066CC` (RGB: 0, 102, 204)
- **AI Cyan**: `#00D9FF` (RGB: 0, 217, 255)
- **Code Green**: `#00FF88` (RGB: 0, 255, 136)

### Secondary Colors
- **Agent Purple**: `#9945FF` (RGB: 153, 69, 255)
- **Warning Amber**: `#FFA500` (RGB: 255, 165, 0)
- **Error Red**: `#FF4444` (RGB: 255, 68, 68)

### Neutral Colors
- **Dark Gray**: `#1E1E1E` (Background)
- **Medium Gray**: `#3C3C3C` (Panels)
- **Light Gray**: `#CCCCCC` (Text)
- **White**: `#FFFFFF` (Highlights)

---

## Logo Design

### ASCII Art Logo (CLI)

```
   ___   ____      _____                      __
  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /
 / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / 
/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  
                      /___/                     
```

### Compact Logo (Terminal Header)

```
🤖 AI-Squad
   Your AI Development Squad
```

### Icon Logo (Emoji-based)

```
🎯 AI-Squad
```

Agent Icons:
- 🎨 Product Manager
- 🏗️ Architect
- 💻 Engineer
- 🎭 UX Designer
- ✅ Reviewer

---

## SVG Logo Concept

**Concept**: Five hexagons arranged in a squad formation, each representing an agent

### Logo Description:

```
     ⬡ (PM)
   ⬡   ⬡  (Arch + UX)
  ⬡     ⬡ (Eng + Review)
```

**Elements**:
- Five hexagons in gradient from blue to cyan
- Connected by thin lines showing collaboration
- Central hexagon slightly larger (PM/Squad leader)
- Modern, geometric, tech-forward aesthetic

---

## Logo Variations

### 1. Full Logo (Horizontal)
```
╔═══════════════════════════════════════════╗
║  ⬡⬡⬡    AI-SQUAD                          ║
║  ⬡⬡     Your AI Development Squad         ║
╚═══════════════════════════════════════════╝
```

### 2. Compact Logo (Square)
```
┌─────────────┐
│    ⬡⬡⬡      │
│    ⬡⬡       │
│  AI-SQUAD   │
└─────────────┘
```

### 3. Icon Only (Minimal)
```
⬡⬡⬡
⬡⬡
```

### 4. Badge Logo
```
╭──────────────╮
│   🎯 AI-SQUAD │
│   v0.3.0     │
╰──────────────╯
```

---

## Terminal UI Elements

### Welcome Banner (Rich Text)
```python
from rich.console import Console
from rich.panel import Panel

console = Console()

banner = """
[bold cyan]   ___   ____      _____                      __[/]
[bold cyan]  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /[/]
[bold cyan] / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / [/]
[bold cyan]/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  [/]
[bold cyan]                      /___/                     [/]
"""

console.print(Panel(
    banner + "\n[bold white]Your AI Development Squad, One Command Away[/]\n[cyan]Version 0.3.0[/]",
    style="cyan",
    border_style="bright_cyan"
))
```

### Agent Status Display
```
┌─────────────────────────────────────────┐
│ 🎨 PM        │ ✅ Ready                 │
│ 🏗️ Architect │ ⚙️  Working...           │
│ 💻 Engineer  │ ⏸️  Waiting              │
│ 🎭 UX        │ ✅ Complete              │
│ ✅ Reviewer  │ 📋 Pending               │
└─────────────────────────────────────────┘
```

---

## Typography

### Font Recommendations

**CLI/Terminal**:
- Primary: `JetBrains Mono` (Code font)
- Alternative: `Fira Code`, `Cascadia Code`

**Documentation**:
- Headings: `Inter`, `Roboto`, `System Sans`
- Body: `Source Sans Pro`, `Open Sans`
- Code: `JetBrains Mono`, `Fira Code`

### Text Styles
- **Headers**: Bold, uppercase, cyan color
- **Success**: Green color with ✅ checkmark
- **Warning**: Yellow/amber with ⚠️ warning icon
- **Error**: Red with ❌ cross
- **Info**: Blue with ℹ️ info icon

---

## Usage Guidelines

### DO ✅
- Use the ASCII logo in CLI banners
- Use emoji icons for agents consistently
- Maintain cyan/blue color scheme
- Keep designs clean and minimal
- Use hexagon motif when possible

### DON'T ❌
- Don't change agent icon associations
- Don't use conflicting colors
- Don't make logos too complex
- Don't use low-contrast combinations
- Don't mix different logo styles in same context

---

## File Recommendations

### For Future Implementation:

1. **Logo Files to Create**:
   - `logo.svg` - SVG vector logo
   - `logo-light.svg` - Light theme variant
   - `logo-dark.svg` - Dark theme variant
   - `icon.png` - Square icon (512x512, 256x256, 128x128, 64x64)
   - `banner.png` - Wide banner (1200x400)

2. **Brand Assets**:
   - `brand-guidelines.pdf` - Full brand guide
   - `color-palette.css` - CSS color variables
   - `agent-icons.svg` - Individual agent icons

3. **Marketing Materials**:
   - `og-image.png` - Open Graph image (1200x630)
   - `twitter-card.png` - Twitter card (1200x675)
   - `github-social.png` - GitHub social preview (1280x640)

---

## Integration Examples

### README.md Header
```markdown
<div align="center">
  
```
   ___   ____      _____                      __
  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /
 / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / 
/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  
                      /___/                     
```

**Your AI Development Squad, One Command Away**

[![PyPI](https://img.shields.io/pypi/v/ai-squad.svg)](https://pypi.org/project/ai-squad/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>
```

### CLI Banner (Current Implementation)
Located in: `ai_squad/cli.py`

### Documentation Site Header
```html
<header class="site-header">
  <div class="logo">
    <span class="hexagon">⬡⬡⬡</span>
    <h1>AI-Squad</h1>
  </div>
  <nav>...</nav>
</header>
```

---

## Next Steps for Branding

1. **Create SVG Logo**: Design professional SVG logo with hexagons
2. **Generate Icon Set**: Create PNG icons in multiple sizes
3. **Update CLI**: Enhance terminal banner with color and styling
4. **Add to README**: Update README with logo
5. **Social Media**: Create social media preview images
6. **Documentation Site**: Design branded documentation site theme

---

## License

All branding assets are part of AI-Squad and licensed under MIT License.

---

**Version**: 1.0  
**Last Updated**: January 22, 2026  
**Maintained By**: AI-Squad Team
