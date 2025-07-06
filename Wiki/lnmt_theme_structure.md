# LNMT (Linux Network Management Toolbox) Theme Modularization Plan

## Ready to Process Your Themes

**Please provide the theme file(s) by:**
1. **Uploading** the main theme file (themes.css or similar)
2. **Sharing** the raw GitHub URL to the theme file
3. **Pasting** the theme file content directly

Once I have the theme content, I'll immediately:
- Parse all existing themes from your master file
- Create individual modular theme files for web (CSS) and CLI (ANSI)
- Generate a complete manifest with metadata
- Provide theme switching functionality
- Create migration documentation

## Expected Output Structure
```
themes/
├── web/
│   ├── themes/
│   │   ├── solarized_dark.css
│   │   ├── solarized_light.css
│   │   ├── matrix.css
│   │   ├── dracula.css
│   │   ├── monokai.css
│   │   ├── nord.css
│   │   ├── gruvbox_dark.css
│   │   ├── gruvbox_light.css
│   │   ├── one_dark.css
│   │   ├── github_dark.css
│   │   └── github_light.css
│   └── theme-loader.js
├── cli/
│   ├── themes/
│   │   ├── solarized_dark.ansi
│   │   ├── solarized_light.ansi
│   │   ├── matrix.ansi
│   │   ├── dracula.ansi
│   │   ├── monokai.ansi
│   │   ├── nord.ansi
│   │   ├── gruvbox_dark.ansi
│   │   ├── gruvbox_light.ansi
│   │   ├── one_dark.ansi
│   │   ├── github_dark.ansi
│   │   └── github_light.ansi
│   └── theme-loader.sh
├── manifest.json
├── README.md
└── migration-guide.md
```

## Theme File Format Standards

### Web Theme Format (CSS)
```css
/**
 * Theme: Solarized Dark
 * Author: Ethan Schoonover
 * Description: Precision colors for machines and people
 * Version: 1.0.0
 * Type: dark
 * Base16: true
 * URL: https://ethanschoonover.com/solarized/
 */

:root {
  /* Base colors */
  --theme-bg-primary: #002b36;
  --theme-bg-secondary: #073642;
  --theme-fg-primary: #839496;
  --theme-fg-secondary: #586e75;
  
  /* Accent colors */
  --theme-accent-1: #268bd2;
  --theme-accent-2: #2aa198;
  --theme-accent-3: #859900;
  --theme-accent-4: #cb4b16;
  --theme-accent-5: #dc322f;
  --theme-accent-6: #d33682;
  --theme-accent-7: #6c71c4;
  --theme-accent-8: #b58900;
  
  /* Semantic colors */
  --theme-success: var(--theme-accent-3);
  --theme-warning: var(--theme-accent-8);
  --theme-error: var(--theme-accent-5);
  --theme-info: var(--theme-accent-1);
}

/* Theme-specific styles */
.theme-solarized-dark {
  background-color: var(--theme-bg-primary);
  color: var(--theme-fg-primary);
}
```

### CLI Theme Format (ANSI)
```bash
#!/bin/bash
# Theme: Solarized Dark
# Author: Ethan Schoonover
# Description: Precision colors for machines and people
# Version: 1.0.0
# Type: dark
# Base16: true
# URL: https://ethanschoonover.com/solarized/

# Base colors
export THEME_BG_PRIMARY="\033[48;5;235m"      # #002b36
export THEME_BG_SECONDARY="\033[48;5;236m"    # #073642
export THEME_FG_PRIMARY="\033[38;5;244m"      # #839496
export THEME_FG_SECONDARY="\033[38;5;240m"    # #586e75

# Accent colors
export THEME_ACCENT_1="\033[38;5;33m"         # #268bd2 (blue)
export THEME_ACCENT_2="\033[38;5;37m"         # #2aa198 (cyan)
export THEME_ACCENT_3="\033[38;5;64m"         # #859900 (green)
export THEME_ACCENT_4="\033[38;5;166m"        # #cb4b16 (orange)
export THEME_ACCENT_5="\033[38;5;160m"        # #dc322f (red)
export THEME_ACCENT_6="\033[38;5;125m"        # #d33682 (magenta)
export THEME_ACCENT_7="\033[38;5;61m"         # #6c71c4 (violet)
export THEME_ACCENT_8="\033[38;5;136m"        # #b58900 (yellow)

# Semantic colors
export THEME_SUCCESS="$THEME_ACCENT_3"
export THEME_WARNING="$THEME_ACCENT_8"
export THEME_ERROR="$THEME_ACCENT_5"
export THEME_INFO="$THEME_ACCENT_1"

# Reset
export THEME_RESET="\033[0m"
```

## Manifest File Structure

### manifest.json
```json
{
  "version": "1.0.0",
  "themes": [
    {
      "id": "solarized_dark",
      "name": "Solarized Dark",
      "author": "Ethan Schoonover",
      "description": "Precision colors for machines and people",
      "version": "1.0.0",
      "type": "dark",
      "base16": true,
      "url": "https://ethanschoonover.com/solarized/",
      "files": {
        "web": "web/themes/solarized_dark.css",
        "cli": "cli/themes/solarized_dark.ansi"
      },
      "colors": {
        "primary": "#002b36",
        "secondary": "#073642",
        "foreground": "#839496",
        "accent": "#268bd2"
      },
      "tags": ["popular", "base16", "professional"]
    }
  ]
}
```

## Implementation Plan

### Phase 1: Parser
1. Create a parser to extract themes from the master file
2. Identify color schemes and naming patterns
3. Generate metadata for each theme

### Phase 2: File Generation
1. Convert themes to CSS format with CSS custom properties
2. Generate ANSI escape sequences for CLI themes
3. Create manifest file with theme metadata

### Phase 3: Loader Systems
1. JavaScript theme loader for web
2. Shell script theme loader for CLI
3. Theme switching functionality

### Phase 4: Documentation
1. Installation guide
2. Theme creation guide
3. Migration instructions
4. API documentation

## Theme Loader Examples

### Web Theme Loader
```javascript
class ThemeManager {
  constructor() {
    this.currentTheme = null;
    this.themes = new Map();
  }
  
  async loadTheme(themeName) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `themes/web/themes/${themeName}.css`;
    document.head.appendChild(link);
    
    this.currentTheme = themeName;
    localStorage.setItem('lnmt-theme', themeName);
  }
  
  async getAvailableThemes() {
    const response = await fetch('themes/manifest.json');
    const manifest = await response.json();
    return manifest.themes;
  }
}
```

### CLI Theme Loader
```bash
#!/bin/bash
# LNMT CLI Theme Loader

THEME_DIR="$(dirname "$0")/themes"

load_theme() {
    local theme_name="$1"
    local theme_file="$THEME_DIR/${theme_name}.ansi"
    
    if [[ -f "$theme_file" ]]; then
        source "$theme_file"
        export LNMT_CURRENT_THEME="$theme_name"
        echo "Theme '${theme_name}' loaded successfully"
    else
        echo "Theme '${theme_name}' not found"
        return 1
    fi
}

list_themes() {
    echo "Available themes:"
    for theme in "$THEME_DIR"/*.ansi; do
        basename "$theme" .ansi
    done
}
```

## Migration Strategy

### From Monolithic to Modular
1. **Backup**: Create backup of existing theme configuration
2. **Extract**: Parse and extract individual themes
3. **Convert**: Transform to new modular format
4. **Test**: Verify all themes work correctly
5. **Deploy**: Replace old system with new modular system

### Compatibility Layer
- Maintain backwards compatibility during transition
- Provide migration scripts for existing configurations
- Support both old and new theme formats temporarily

## Benefits

1. **Modularity**: Easy to add, remove, or modify individual themes
2. **Sharing**: Themes can be shared independently
3. **Maintenance**: Easier to maintain and update individual themes
4. **Performance**: Load only required themes
5. **Organization**: Clear structure and metadata