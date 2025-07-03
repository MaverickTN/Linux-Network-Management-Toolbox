#!/usr/bin/env python3
"""
LNMT Theme Parser & Modularization System
Converts the monolithic themes.py into modular theme files for web and CLI
"""

import os
import json
import yaml
from pathlib import Path

# Your existing theme data
THEMES = {
    "dark": {
        "name": "Dark",
        "primary": "#3498db",
        "background": "#23272e",
        "foreground": "#e0e0e0",
        "accent": "#f39c12",
        "danger": "#e74c3c",
        "success": "#43a047",
        "warning": "#ff9800",
        "info": "#007bff",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[94m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "light": {
        "name": "Light",
        "primary": "#007bff",
        "background": "#f5f6fa",
        "foreground": "#222426",
        "accent": "#39b385",
        "danger": "#c0392b",
        "success": "#388e3c",
        "warning": "#ffb300",
        "info": "#1565c0",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[34m",
            "success": "\033[32m",
            "danger": "\033[31m",
            "warning": "\033[33m",
            "reset": "\033[0m"
        }
    },
    "black": {
        "name": "Blackout",
        "primary": "#18ffff",
        "background": "#000000",
        "foreground": "#c7c7c7",
        "accent": "#00bcd4",
        "danger": "#ff1744",
        "success": "#00e676",
        "warning": "#ff9100",
        "info": "#00b0ff",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[96m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "solarized": {
        "name": "Solarized",
        "primary": "#268bd2",
        "background": "#002b36",
        "foreground": "#93a1a1",
        "accent": "#b58900",
        "danger": "#dc322f",
        "success": "#859900",
        "warning": "#cb4b16",
        "info": "#839496",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[94m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "oceanic": {
        "name": "Oceanic",
        "primary": "#29b6f6",
        "background": "#22313f",
        "foreground": "#b0bec5",
        "accent": "#ffd54f",
        "danger": "#e53935",
        "success": "#43a047",
        "warning": "#ffa726",
        "info": "#0288d1",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[96m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "nord": {
        "name": "Nord",
        "primary": "#81A1C1",
        "background": "#2E3440",
        "foreground": "#D8DEE9",
        "accent": "#A3BE8C",
        "danger": "#BF616A",
        "success": "#A3BE8C",
        "warning": "#EBCB8B",
        "info": "#5E81AC",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[94m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "gruvbox": {
        "name": "Gruvbox",
        "primary": "#fabd2f",
        "background": "#282828",
        "foreground": "#ebdbb2",
        "accent": "#b8bb26",
        "danger": "#fb4934",
        "success": "#b8bb26",
        "warning": "#fe8019",
        "info": "#83a598",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[93m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "material": {
        "name": "Material",
        "primary": "#2196f3",
        "background": "#263238",
        "foreground": "#ececec",
        "accent": "#ffeb3b",
        "danger": "#e53935",
        "success": "#43a047",
        "warning": "#fbc02d",
        "info": "#00bcd4",
        "border-radius": "10px",
        "cli": {
            "primary": "\033[94m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "retro_terminal": {
        "name": "Retro Terminal",
        "primary": "#39FF14",
        "background": "#1a1a1a",
        "foreground": "#e0e0e0",
        "accent": "#FFFF00",
        "danger": "#FF3131",
        "success": "#00FF41",
        "warning": "#FFD700",
        "info": "#00BFFF",
        "border-radius": "0px",
        "cli": {
            "primary": "\033[92m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    },
    "matrix": {
        "name": "Green Matrix",
        "primary": "#00ff41",
        "background": "#101010",
        "foreground": "#bada55",
        "accent": "#00ff41",
        "danger": "#ff1133",
        "success": "#21f300",
        "warning": "#ffea00",
        "info": "#43d9ad",
        "border-radius": "5px",
        "cli": {
            "primary": "\033[92m",
            "success": "\033[92m",
            "danger": "\033[91m",
            "warning": "\033[93m",
            "reset": "\033[0m"
        }
    }
}

def create_directory_structure():
    """Create the directory structure for modular themes"""
    directories = [
        "themes/web/themes",
        "themes/cli/themes",
        "themes/docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created directory structure")

def generate_css_theme(theme_id, theme_data):
    """Generate CSS file for a theme"""
    theme_type = "dark" if is_dark_theme(theme_data) else "light"
    
    css_content = f"""/**
 * Theme: {theme_data['name']}
 * ID: {theme_id}
 * Type: {theme_type}
 * Description: LNMT {theme_data['name']} theme
 * Version: 1.0.0
 * Author: LNMT Project
 */

:root {{
  /* Primary Colors */
  --lnmt-primary: {theme_data['primary']};
  --lnmt-background: {theme_data['background']};
  --lnmt-foreground: {theme_data['foreground']};
  --lnmt-accent: {theme_data['accent']};
  
  /* Status Colors */
  --lnmt-danger: {theme_data['danger']};
  --lnmt-success: {theme_data['success']};
  --lnmt-warning: {theme_data['warning']};
  --lnmt-info: {theme_data['info']};
  
  /* Layout */
  --lnmt-border-radius: {theme_data['border-radius']};
}}

/* Theme Base Styles */
.theme-{theme_id} {{
  background-color: var(--lnmt-background);
  color: var(--lnmt-foreground);
}}

.theme-{theme_id} .primary {{
  color: var(--lnmt-primary);
}}

.theme-{theme_id} .accent {{
  color: var(--lnmt-accent);
}}

.theme-{theme_id} .success {{
  color: var(--lnmt-success);
}}

.theme-{theme_id} .danger {{
  color: var(--lnmt-danger);
}}

.theme-{theme_id} .warning {{
  color: var(--lnmt-warning);
}}

.theme-{theme_id} .info {{
  color: var(--lnmt-info);
}}

/* Component Styles */
.theme-{theme_id} .btn {{
  border-radius: var(--lnmt-border-radius);
  border: 1px solid var(--lnmt-primary);
  background: var(--lnmt-primary);
  color: var(--lnmt-background);
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}}

.theme-{theme_id} .btn:hover {{
  background: var(--lnmt-accent);
  border-color: var(--lnmt-accent);
}}

.theme-{theme_id} .card {{
  background: var(--lnmt-background);
  border: 1px solid var(--lnmt-primary);
  border-radius: var(--lnmt-border-radius);
  padding: 1rem;
  margin: 0.5rem 0;
}}

.theme-{theme_id} .input {{
  background: var(--lnmt-background);
  border: 1px solid var(--lnmt-primary);
  border-radius: var(--lnmt-border-radius);
  color: var(--lnmt-foreground);
  padding: 8px 12px;
}}

.theme-{theme_id} .input:focus {{
  border-color: var(--lnmt-accent);
  outline: none;
  box-shadow: 0 0 0 2px rgba({hex_to_rgb(theme_data['accent'])}, 0.2);
}}

/* Status Classes */
.theme-{theme_id} .alert-success {{
  background: rgba({hex_to_rgb(theme_data['success'])}, 0.1);
  border: 1px solid var(--lnmt-success);
  color: var(--lnmt-success);
}}

.theme-{theme_id} .alert-danger {{
  background: rgba({hex_to_rgb(theme_data['danger'])}, 0.1);
  border: 1px solid var(--lnmt-danger);
  color: var(--lnmt-danger);
}}

.theme-{theme_id} .alert-warning {{
  background: rgba({hex_to_rgb(theme_data['warning'])}, 0.1);
  border: 1px solid var(--lnmt-warning);
  color: var(--lnmt-warning);
}}

.theme-{theme_id} .alert-info {{
  background: rgba({hex_to_rgb(theme_data['info'])}, 0.1);
  border: 1px solid var(--lnmt-info);
  color: var(--lnmt-info);
}}
"""
    
    return css_content

def generate_cli_theme(theme_id, theme_data):
    """Generate CLI/ANSI theme file"""
    cli_data = theme_data.get('cli', {})
    
    cli_content = f"""#!/bin/bash
# Theme: {theme_data['name']}
# ID: {theme_id}
# Type: {"dark" if is_dark_theme(theme_data) else "light"}
# Description: LNMT {theme_data['name']} CLI theme
# Version: 1.0.0
# Author: LNMT Project

# ANSI Color Codes
export LNMT_CLI_PRIMARY="{cli_data.get('primary', '\\033[94m')}"
export LNMT_CLI_SUCCESS="{cli_data.get('success', '\\033[92m')}"
export LNMT_CLI_DANGER="{cli_data.get('danger', '\\033[91m')}"
export LNMT_CLI_WARNING="{cli_data.get('warning', '\\033[93m')}"
export LNMT_CLI_RESET="{cli_data.get('reset', '\\033[0m')}"

# Extended Colors (256-color support)
export LNMT_CLI_BACKGROUND="\\033[48;2;{hex_to_rgb_values(theme_data['background'])}m"
export LNMT_CLI_FOREGROUND="\\033[38;2;{hex_to_rgb_values(theme_data['foreground'])}m"
export LNMT_CLI_ACCENT="\\033[38;2;{hex_to_rgb_values(theme_data['accent'])}m"
export LNMT_CLI_INFO="\\033[38;2;{hex_to_rgb_values(theme_data['info'])}m"

# Theme Functions
lnmt_print_primary() {{
    echo -e "${{LNMT_CLI_PRIMARY}}$1${{LNMT_CLI_RESET}}"
}}

lnmt_print_success() {{
    echo -e "${{LNMT_CLI_SUCCESS}}✅ $1${{LNMT_CLI_RESET}}"
}}

lnmt_print_danger() {{
    echo -e "${{LNMT_CLI_DANGER}}❌ $1${{LNMT_CLI_RESET}}"
}}

lnmt_print_warning() {{
    echo -e "${{LNMT_CLI_WARNING}}⚠️  $1${{LNMT_CLI_RESET}}"
}}

lnmt_print_info() {{
    echo -e "${{LNMT_CLI_INFO}}ℹ️  $1${{LNMT_CLI_RESET}}"
}}

# Theme Metadata
export LNMT_THEME_NAME="{theme_data['name']}"
export LNMT_THEME_ID="{theme_id}"
export LNMT_THEME_TYPE="{"dark" if is_dark_theme(theme_data) else "light"}"

# Usage Examples (uncomment to test)
# lnmt_print_primary "Primary message"
# lnmt_print_success "Operation completed successfully"
# lnmt_print_danger "Error occurred"
# lnmt_print_warning "Warning message"
# lnmt_print_info "Information message"
"""
    
    return cli_content

def hex_to_rgb(hex_color):
    """Convert hex color to RGB values"""
    hex_color = hex_color.lstrip('#')
    return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))

def hex_to_rgb_values(hex_color):
    """Convert hex color to RGB values for ANSI"""
    hex_color = hex_color.lstrip('#')
    return ';'.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))

def is_dark_theme(theme_data):
    """Determine if theme is dark based on background color"""
    bg = theme_data['background'].lstrip('#')
    r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5

def generate_manifest():
    """Generate theme manifest file"""
    manifest = {
        "version": "1.0.0",
        "name": "LNMT Themes",
        "description": "Modular theme collection for Linux Network Management Toolbox",
        "author": "LNMT Project",
        "themes": []
    }
    
    for theme_id, theme_data in THEMES.items():
        theme_info = {
            "id": theme_id,
            "name": theme_data['name'],
            "type": "dark" if is_dark_theme(theme_data) else "light",
            "description": f"LNMT {theme_data['name']} theme",
            "version": "1.0.0",
            "files": {
                "web": f"web/themes/{theme_id}.css",
                "cli": f"cli/themes/{theme_id}.sh"
            },
            "colors": {
                "primary": theme_data['primary'],
                "background": theme_data['background'],
                "foreground": theme_data['foreground'],
                "accent": theme_data['accent']
            },
            "features": {
                "web_support": True,
                "cli_support": True,
                "ansi_256_color": True,
                "responsive": True
            }
        }
        manifest["themes"].append(theme_info)
    
    return manifest

def generate_theme_loader_js():
    """Generate JavaScript theme loader for web"""
    js_content = """/**
 * LNMT Web Theme Loader
 * Handles dynamic theme switching for web interface
 */

class LNMTThemeManager {
    constructor() {
        this.currentTheme = null;
        this.themes = new Map();
        this.initialized = false;
    }

    async init() {
        try {
            const response = await fetch('/themes/manifest.json');
            const manifest = await response.json();
            
            manifest.themes.forEach(theme => {
                this.themes.set(theme.id, theme);
            });
            
            // Load saved theme or default
            const savedTheme = localStorage.getItem('lnmt-theme') || 'dark';
            await this.loadTheme(savedTheme);
            
            this.initialized = true;
            console.log('✅ LNMT Theme Manager initialized');
        } catch (error) {
            console.error('❌ Failed to initialize theme manager:', error);
        }
    }

    async loadTheme(themeId) {
        if (!this.themes.has(themeId)) {
            console.error(`Theme "${themeId}" not found`);
            return false;
        }

        try {
            // Remove existing theme
            this.removeCurrentTheme();
            
            // Load new theme CSS
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = `/themes/${this.themes.get(themeId).files.web}`;
            link.id = 'lnmt-theme-css';
            document.head.appendChild(link);
            
            // Apply theme class
            document.body.className = document.body.className.replace(/theme-\\w+/g, '');
            document.body.classList.add(`theme-${themeId}`);
            
            this.currentTheme = themeId;
            localStorage.setItem('lnmt-theme', themeId);
            
            // Dispatch theme change event
            window.dispatchEvent(new CustomEvent('lnmt-theme-changed', {
                detail: { themeId, theme: this.themes.get(themeId) }
            }));
            
            return true;
        } catch (error) {
            console.error(`Failed to load theme "${themeId}":`, error);
            return false;
        }
    }

    removeCurrentTheme() {
        const existing = document.getElementById('lnmt-theme-css');
        if (existing) {
            existing.remove();
        }
    }

    getThemes() {
        return Array.from(this.themes.values());
    }

    getCurrentTheme() {
        return this.currentTheme;
    }

    getThemeInfo(themeId) {
        return this.themes.get(themeId);
    }

    async toggleTheme() {
        const themes = this.getThemes();
        const currentIndex = themes.findIndex(t => t.id === this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;
        await this.loadTheme(themes[nextIndex].id);
    }
}

// Global instance
window.lnmtThemes = new LNMTThemeManager();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.lnmtThemes.init());
} else {
    window.lnmtThemes.init();
}
"""
    
    return js_content

def generate_theme_loader_sh():
    """Generate shell script theme loader for CLI"""
    sh_content = """#!/bin/bash
# LNMT CLI Theme Loader
# Handles theme switching for CLI interface

THEME_DIR="$(dirname "$0")/themes"
CURRENT_THEME_FILE="$HOME/.lnmt_theme"

# Colors for loader messages
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

lnmt_theme_load() {
    local theme_name="$1"
    local theme_file="$THEME_DIR/${theme_name}.sh"
    
    if [[ ! -f "$theme_file" ]]; then
        echo -e "${RED}❌ Theme '${theme_name}' not found${NC}"
        echo -e "${YELLOW}Available themes:${NC}"
        lnmt_theme_list
        return 1
    fi
    
    # Source the theme file
    source "$theme_file"
    
    # Save current theme
    echo "$theme_name" > "$CURRENT_THEME_FILE"
    
    echo -e "${GREEN}✅ Theme '${LNMT_THEME_NAME}' loaded successfully${NC}"
    return 0
}

lnmt_theme_list() {
    echo -e "${BLUE}Available LNMT themes:${NC}"
    for theme in "$THEME_DIR"/*.sh; do
        if [[ -f "$theme" ]]; then
            local theme_name=$(basename "$theme" .sh)
            local current_marker=""
            
            if [[ -f "$CURRENT_THEME_FILE" ]]; then
                local current_theme=$(cat "$CURRENT_THEME_FILE")
                [[ "$current_theme" == "$theme_name" ]] && current_marker=" ${GREEN}(current)${NC}"
            fi
            
            echo -e "  • $theme_name$current_marker"
        fi
    done
}

lnmt_theme_info() {
    local theme_name="$1"
    local theme_file="$THEME_DIR/${theme_name}.sh"
    
    if [[ ! -f "$theme_file" ]]; then
        echo -e "${RED}❌ Theme '${theme_name}' not found${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Theme Information:${NC}"
    grep "^# " "$theme_file" | head -6
}

lnmt_theme_current() {
    if [[ -f "$CURRENT_THEME_FILE" ]]; then
        local current_theme=$(cat "$CURRENT_THEME_FILE")
        echo -e "${GREEN}Current theme: $current_theme${NC}"
        
        if [[ -n "$LNMT_THEME_NAME" ]]; then
            echo -e "${BLUE}Loaded: $LNMT_THEME_NAME ($LNMT_THEME_TYPE)${NC}"
        fi
    else
        echo -e "${YELLOW}No theme currently loaded${NC}"
    fi
}

lnmt_theme_reset() {
    unset LNMT_CLI_PRIMARY LNMT_CLI_SUCCESS LNMT_CLI_DANGER LNMT_CLI_WARNING LNMT_CLI_RESET
    unset LNMT_CLI_BACKGROUND LNMT_CLI_FOREGROUND LNMT_CLI_ACCENT LNMT_CLI_INFO
    unset LNMT_THEME_NAME LNMT_THEME_ID LNMT_THEME_TYPE
    [[ -f "$CURRENT_THEME_FILE" ]] && rm "$CURRENT_THEME_FILE"
    echo -e "${GREEN}✅ Theme reset completed${NC}"
}

# Auto-load saved theme
if [[ -f "$CURRENT_THEME_FILE" ]]; then
    saved_theme=$(cat "$CURRENT_THEME_FILE")
    lnmt_theme_load "$saved_theme" > /dev/null 2>&1
fi

# Main CLI handler
case "${1:-}" in
    "load")
        lnmt_theme_load "$2"
        ;;
    "list"|"ls")
        lnmt_theme_list
        ;;
    "info")
        lnmt_theme_info "$2"
        ;;
    "current")
        lnmt_theme_current
        ;;
    "reset")
        lnmt_theme_reset
        ;;
    *)
        echo -e "${BLUE}LNMT Theme Loader${NC}"
        echo "Usage: $0 {load|list|info|current|reset} [theme_name]"
        echo ""
        echo "Commands:"
        echo "  load <theme>  - Load a theme"
        echo "  list          - List available themes"
        echo "  info <theme>  - Show theme information"
        echo "  current       - Show current theme"
        echo "  reset         - Reset to no theme"
        ;;
esac
"""
    
    return sh_content

def create_all_files():
    """Create all theme files and supporting files"""
    print("🚀 Starting LNMT theme modularization...")
    
    # Create directory structure
    create_directory_structure()
    
    # Generate individual theme files
    for theme_id, theme_data in THEMES.items():
        # Web CSS file
        css_content = generate_css_theme(theme_id, theme_data)
        css_path = f"themes/web/themes/{theme_id}.css"
        with open(css_path, 'w') as f:
            f.write(css_content)
        print(f"✅ Created web theme: {css_path}")
        
        # CLI shell file
        cli_content = generate_cli_theme(theme_id, theme_data)
        cli_path = f"themes/cli/themes/{theme_id}.sh"
        with open(cli_path, 'w') as f:
            f.write(cli_content)
        os.chmod(cli_path, 0o755)  # Make executable
        print(f"✅ Created CLI theme: {cli_path}")
    
    # Generate manifest
    manifest = generate_manifest()
    with open("themes/manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    print("✅ Created manifest.json")
    
    # Generate YAML manifest
    with open("themes/manifest.yml", 'w') as f:
        yaml.dump(manifest, f, default_flow_style=False, indent=2)
    print("✅ Created manifest.yml")
    
    # Generate theme loaders
    js_content = generate_theme_loader_js()
    with open("themes/web/theme-loader.js", 'w') as f:
        f.write(js_content)
    print("✅ Created web theme loader")
    
    sh_content = generate_theme_loader_sh()
    with open("themes/cli/theme-loader.sh", 'w') as f:
        f.write(sh_content)
    os.chmod("themes/cli/theme-loader.sh", 0o755)  # Make executable
    print("✅ Created CLI theme loader")
    
    print(f"\\n🎉 Successfully created {len(THEMES)} modular themes!")
    print(f"📁 Files created in: themes/")

if __name__ == "__main__":
    create_all_files()
