#!/usr/bin/env python3
"""
LNMT Drop-In Theme System
Creates individual .theme files that are self-contained CLI/web theme pairs
"""

import os
import json
import re
from pathlib import Path
from textwrap import dedent

# Your existing theme data
THEMES = {
    "dark": {
        "name": "Dark",
        "author": "LNMT Team",
        "description": "Clean dark theme with blue accents",
        "version": "1.0.0",
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
        "author": "LNMT Team", 
        "description": "Professional light theme for daytime use",
        "version": "1.0.0",
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
    "solarized": {
        "name": "Solarized",
        "author": "Ethan Schoonover",
        "description": "Precision colors for machines and people",
        "version": "1.0.0",
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
    "matrix": {
        "name": "Green Matrix",
        "author": "LNMT Team",
        "description": "Matrix-inspired green on black theme",
        "version": "1.0.0",
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

def create_themes_directory():
    """Create the themes directory structure"""
    Path("themes").mkdir(exist_ok=True)
    print("✅ Created themes directory")

def hex_to_rgb(hex_color):
    """Convert hex color to RGB values"""
    hex_color = hex_color.lstrip('#')
    return ', '.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))

def hex_to_rgb_shell(hex_color):
    """Convert hex to RGB for shell (semicolon separated)"""
    hex_color = hex_color.lstrip('#')
    return ';'.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))

def is_dark_theme(theme_data):
    """Determine if theme is dark"""
    bg = theme_data['background'].lstrip('#')
    r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5

def generate_theme_file(theme_id, theme_data):
    """Generate a complete .theme file with embedded CSS and shell code"""
    
    theme_type = "dark" if is_dark_theme(theme_data) else "light"
    cli_data = theme_data.get('cli', {})
    
    # Create the .theme file content
    theme_content = f'''#!/usr/bin/env lnmt-theme
# LNMT Theme File - {theme_data['name']}
# Drop this file in your themes/ folder and it will be auto-detected

# === THEME METADATA ===
THEME_ID="{theme_id}"
THEME_NAME="{theme_data['name']}"
THEME_AUTHOR="{theme_data.get('author', 'Unknown')}"
THEME_DESCRIPTION="{theme_data.get('description', 'No description')}"
THEME_VERSION="{theme_data.get('version', '1.0.0')}"
THEME_TYPE="{theme_type}"

# === COLOR PALETTE ===
PRIMARY="{theme_data['primary']}"
BACKGROUND="{theme_data['background']}"
FOREGROUND="{theme_data['foreground']}"
ACCENT="{theme_data['accent']}"
SUCCESS="{theme_data['success']}"
DANGER="{theme_data['danger']}"
WARNING="{theme_data['warning']}"
INFO="{theme_data['info']}"
BORDER_RADIUS="{theme_data['border-radius']}"

# === WEB CSS (Embedded) ===
read -r -d '' THEME_WEB_CSS << 'EOF_CSS'
/* LNMT Theme: {theme_data['name']} - Web Interface */
.lnmt-theme-{theme_id} {{
  --primary: {theme_data['primary']};
  --background: {theme_data['background']};
  --foreground: {theme_data['foreground']};
  --accent: {theme_data['accent']};
  --success: {theme_data['success']};
  --danger: {theme_data['danger']};
  --warning: {theme_data['warning']};
  --info: {theme_data['info']};
  --border-radius: {theme_data['border-radius']};
  
  background: var(--background);
  color: var(--foreground);
  transition: all 0.3s ease;
}}

.lnmt-theme-{theme_id} .btn {{
  background: var(--primary);
  color: var(--background);
  border: 2px solid var(--primary);
  border-radius: var(--border-radius);
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
}}

.lnmt-theme-{theme_id} .btn:hover {{
  opacity: 0.8;
  transform: translateY(-1px);
}}

.lnmt-theme-{theme_id} .card {{
  background: var(--background);
  border: 2px solid var(--primary);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  margin: 1rem 0;
}}

.lnmt-theme-{theme_id} .input {{
  background: var(--background);
  border: 2px solid var(--primary);
  border-radius: var(--border-radius);
  color: var(--foreground);
  padding: 0.75rem 1rem;
}}

.lnmt-theme-{theme_id} .text-primary {{ color: var(--primary); }}
.lnmt-theme-{theme_id} .text-success {{ color: var(--success); }}
.lnmt-theme-{theme_id} .text-danger {{ color: var(--danger); }}
.lnmt-theme-{theme_id} .text-warning {{ color: var(--warning); }}
.lnmt-theme-{theme_id} .text-info {{ color: var(--info); }}
.lnmt-theme-{theme_id} .text-accent {{ color: var(--accent); }}

.lnmt-theme-{theme_id} .alert {{
  padding: 1rem;
  border-radius: var(--border-radius);
  border-left: 4px solid;
  margin: 1rem 0;
}}

.lnmt-theme-{theme_id} .alert-success {{
  background: rgba({hex_to_rgb(theme_data['success'])}, 0.1);
  border-color: var(--success);
  color: var(--success);
}}

.lnmt-theme-{theme_id} .alert-danger {{
  background: rgba({hex_to_rgb(theme_data['danger'])}, 0.1);
  border-color: var(--danger);
  color: var(--danger);
}}

.lnmt-theme-{theme_id} .alert-warning {{
  background: rgba({hex_to_rgb(theme_data['warning'])}, 0.1);
  border-color: var(--warning);
  color: var(--warning);
}}

.lnmt-theme-{theme_id} .alert-info {{
  background: rgba({hex_to_rgb(theme_data['info'])}, 0.1);
  border-color: var(--info);
  color: var(--info);
}}
EOF_CSS

# === CLI SHELL COLORS (Embedded) ===
# Basic ANSI Colors
export LNMT_CLI_PRIMARY="{cli_data.get('primary', '\\033[94m')}"
export LNMT_CLI_SUCCESS="{cli_data.get('success', '\\033[92m')}"
export LNMT_CLI_DANGER="{cli_data.get('danger', '\\033[91m')}"
export LNMT_CLI_WARNING="{cli_data.get('warning', '\\033[93m')}"
export LNMT_CLI_RESET="{cli_data.get('reset', '\\033[0m')}"

# True Color Support
export LNMT_CLI_BG="\\033[48;2;{hex_to_rgb_shell(theme_data['background'])}m"
export LNMT_CLI_FG="\\033[38;2;{hex_to_rgb_shell(theme_data['foreground'])}m"
export LNMT_CLI_ACCENT="\\033[38;2;{hex_to_rgb_shell(theme_data['accent'])}m"
export LNMT_CLI_INFO="\\033[38;2;{hex_to_rgb_shell(theme_data['info'])}m"

# CLI Helper Functions
lnmt_print_primary() {{ echo -e "${{LNMT_CLI_PRIMARY}}$1${{LNMT_CLI_RESET}}"; }}
lnmt_print_success() {{ echo -e "${{LNMT_CLI_SUCCESS}}✅ $1${{LNMT_CLI_RESET}}"; }}
lnmt_print_danger() {{ echo -e "${{LNMT_CLI_DANGER}}❌ $1${{LNMT_CLI_RESET}}"; }}
lnmt_print_warning() {{ echo -e "${{LNMT_CLI_WARNING}}⚠️  $1${{LNMT_CLI_RESET}}"; }}
lnmt_print_info() {{ echo -e "${{LNMT_CLI_INFO}}ℹ️  $1${{LNMT_CLI_RESET}}"; }}

lnmt_banner() {{
    echo -e "${{LNMT_CLI_PRIMARY}}╔════════════════════════════════════════╗${{LNMT_CLI_RESET}}"
    echo -e "${{LNMT_CLI_PRIMARY}}║${{LNMT_CLI_RESET}}    LNMT - ${{1:-Network Management}}    ${{LNMT_CLI_PRIMARY}}║${{LNMT_CLI_RESET}}"
    echo -e "${{LNMT_CLI_PRIMARY}}╚════════════════════════════════════════╝${{LNMT_CLI_RESET}}"
}}

# === THEME FUNCTIONS ===

# Load web theme (inject CSS)
lnmt_load_web_theme() {{
    # Create or update style element
    if [ -n "${{THEME_WEB_CSS}}" ]; then
        echo "${{THEME_WEB_CSS}}"
    fi
}}

# Test CLI colors
lnmt_test_cli_colors() {{
    echo "Testing {theme_data['name']} CLI colors:"
    lnmt_print_primary "Primary message"
    lnmt_print_success "Success message"
    lnmt_print_danger "Danger message"  
    lnmt_print_warning "Warning message"
    lnmt_print_info "Info message"
    echo -e "${{LNMT_CLI_ACCENT}}Accent color${{LNMT_CLI_RESET}}"
}}

# Get theme info
lnmt_get_theme_info() {{
    cat << EOF
Theme: ${{THEME_NAME}}
ID: ${{THEME_ID}}
Author: ${{THEME_AUTHOR}}
Version: ${{THEME_VERSION}}
Type: ${{THEME_TYPE}}
Description: ${{THEME_DESCRIPTION}}
EOF
}}

# === AUTO-INITIALIZATION ===
# Export theme metadata for scripts to use
export LNMT_ACTIVE_THEME="${{THEME_ID}}"
export LNMT_ACTIVE_THEME_NAME="${{THEME_NAME}}"
export LNMT_ACTIVE_THEME_TYPE="${{THEME_TYPE}}"

# Print theme loaded message when sourced
if [ "${{BASH_SOURCE[0]}}" != "${{0}}" ]; then
    lnmt_print_success "Theme '${{THEME_NAME}}' loaded"
fi

# === USAGE EXAMPLES ===
# 
# CLI Usage:
#   source themes/{theme_id}.theme
#   lnmt_print_success "Connected to network"
#   lnmt_banner "System Status"
#   lnmt_test_cli_colors
#
# Web Usage:
#   <style id="lnmt-theme"></style>
#   <script>
#     fetch('themes/{theme_id}.theme')
#       .then(r => r.text())
#       .then(theme => {{
#         const css = theme.match(/read -r -d '' THEME_WEB_CSS << 'EOF_CSS'([\\s\\S]*?)EOF_CSS/)[1];
#         document.getElementById('lnmt-theme').textContent = css;
#         document.body.className = 'lnmt-theme-{theme_id}';
#       }});
#   </script>
'''

    return theme_content

def create_theme_index_system():
    """Create the theme indexing and loader system"""
    
    # Theme Manager JavaScript
    theme_manager_js = '''/**
 * LNMT Theme Manager - Handles .theme file loading and indexing
 */

class LNMTThemeManager {
    constructor(themesPath = 'themes/') {
        this.themesPath = themesPath;
        this.themes = new Map();
        this.currentTheme = null;
    }

    /**
     * Scan themes directory and index all .theme files
     */
    async indexThemes() {
        try {
            // Get list of .theme files from directory
            const response = await fetch(`${this.themesPath}index.json`);
            if (!response.ok) {
                // Fallback: try to discover themes
                await this.discoverThemes();
                return;
            }
            
            const index = await response.json();
            this.themes.clear();
            
            for (const themeFile of index.themes) {
                try {
                    const theme = await this.loadThemeFile(themeFile);
                    if (theme) {
                        this.themes.set(theme.id, theme);
                    }
                } catch (error) {
                    console.warn(`Failed to load theme ${themeFile}:`, error);
                }
            }
            
            console.log(`✅ Indexed ${this.themes.size} themes`);
            
        } catch (error) {
            console.error('Failed to index themes:', error);
            await this.discoverThemes();
        }
    }

    /**
     * Fallback theme discovery method
     */
    async discoverThemes() {
        const knownThemes = ['dark.theme', 'light.theme', 'solarized.theme', 'matrix.theme'];
        
        for (const themeFile of knownThemes) {
            try {
                const theme = await this.loadThemeFile(themeFile);
                if (theme) {
                    this.themes.set(theme.id, theme);
                }
            } catch (error) {
                // Theme file doesn't exist, skip
            }
        }
    }

    /**
     * Load and parse a .theme file
     */
    async loadThemeFile(filename) {
        const response = await fetch(`${this.themesPath}${filename}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const content = await response.text();
        return this.parseThemeFile(content, filename);
    }

    /**
     * Parse .theme file content
     */
    parseThemeFile(content, filename) {
        const theme = {
            filename: filename,
            id: this.extractValue(content, 'THEME_ID'),
            name: this.extractValue(content, 'THEME_NAME'),
            author: this.extractValue(content, 'THEME_AUTHOR'),
            description: this.extractValue(content, 'THEME_DESCRIPTION'),
            version: this.extractValue(content, 'THEME_VERSION'),
            type: this.extractValue(content, 'THEME_TYPE'),
            colors: {
                primary: this.extractValue(content, 'PRIMARY'),
                background: this.extractValue(content, 'BACKGROUND'),
                foreground: this.extractValue(content, 'FOREGROUND'),
                accent: this.extractValue(content, 'ACCENT'),
                success: this.extractValue(content, 'SUCCESS'),
                danger: this.extractValue(content, 'DANGER'),
                warning: this.extractValue(content, 'WARNING'),
                info: this.extractValue(content, 'INFO')
            }
        };

        // Extract CSS content
        const cssMatch = content.match(/read -r -d '' THEME_WEB_CSS << 'EOF_CSS'([\\s\\S]*?)EOF_CSS/);
        if (cssMatch) {
            theme.css = cssMatch[1].trim();
        }

        return theme;
    }

    /**
     * Extract variable value from theme file
     */
    extractValue(content, varName) {
        const match = content.match(new RegExp(`${varName}="([^"]*)"`, 'm'));
        return match ? match[1] : '';
    }

    /**
     * Apply a theme to the web interface
     */
    async applyTheme(themeId) {
        const theme = this.themes.get(themeId);
        if (!theme) {
            throw new Error(`Theme '${themeId}' not found`);
        }

        // Remove existing theme classes
        document.body.className = document.body.className.replace(/lnmt-theme-\\w+/g, '');
        
        // Remove existing theme style
        const existingStyle = document.getElementById('lnmt-active-theme');
        if (existingStyle) {
            existingStyle.remove();
        }

        // Add new theme CSS
        const style = document.createElement('style');
        style.id = 'lnmt-active-theme';
        style.textContent = theme.css;
        document.head.appendChild(style);

        // Apply theme class
        document.body.classList.add(`lnmt-theme-${themeId}`);

        this.currentTheme = themeId;
        localStorage.setItem('lnmt-active-theme', themeId);

        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('lnmt-theme-changed', {
            detail: { themeId, theme }
        }));

        return true;
    }

    /**
     * Get all available themes
     */
    getThemes() {
        return Array.from(this.themes.values());
    }

    /**
     * Get specific theme info
     */
    getTheme(themeId) {
        return this.themes.get(themeId);
    }

    /**
     * Populate a select element with available themes
     */
    populateSelector(selectElement) {
        selectElement.innerHTML = '<option value="">Select Theme...</option>';
        
        this.getThemes().forEach(theme => {
            const option = document.createElement('option');
            option.value = theme.id;
            option.textContent = `${theme.name} (${theme.type})`;
            if (theme.id === this.currentTheme) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    /**
     * Initialize theme manager
     */
    async init() {
        await this.indexThemes();
        
        // Load saved theme or default
        const savedTheme = localStorage.getItem('lnmt-active-theme') || 'dark';
        if (this.themes.has(savedTheme)) {
            await this.applyTheme(savedTheme);
        }

        return this;
    }
}

// Global instance
window.lnmtThemes = new LNMTThemeManager();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.lnmtThemes.init());
} else {
    window.lnmtThemes.init();
}'''

    # CLI Theme Manager
    cli_manager = '''#!/bin/bash
# LNMT CLI Theme Manager - Handles .theme files for CLI

THEMES_DIR="${LNMT_THEMES_DIR:-./themes}"
CURRENT_THEME_FILE="$HOME/.lnmt_current_theme"

# Colors for messages
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

lnmt_theme_list() {
    echo -e "${BLUE}Available LNMT Themes:${NC}"
    echo
    
    if [ ! -d "$THEMES_DIR" ]; then
        echo -e "${RED}Themes directory not found: $THEMES_DIR${NC}"
        return 1
    fi
    
    local current_theme=""
    if [ -f "$CURRENT_THEME_FILE" ]; then
        current_theme=$(cat "$CURRENT_THEME_FILE")
    fi
    
    for theme_file in "$THEMES_DIR"/*.theme; do
        if [ -f "$theme_file" ]; then
            local theme_id=$(grep '^THEME_ID=' "$theme_file" | cut -d'"' -f2)
            local theme_name=$(grep '^THEME_NAME=' "$theme_file" | cut -d'"' -f2)
            local theme_type=$(grep '^THEME_TYPE=' "$theme_file" | cut -d'"' -f2)
            local theme_author=$(grep '^THEME_AUTHOR=' "$theme_file" | cut -d'"' -f2)
            
            local marker=""
            if [ "$theme_id" = "$current_theme" ]; then
                marker=" ${GREEN}(active)${NC}"
            fi
            
            echo -e "  ${YELLOW}$theme_id${NC} - $theme_name [$theme_type] by $theme_author$marker"
        fi
    done
}

lnmt_theme_load() {
    local theme_id="$1"
    
    if [ -z "$theme_id" ]; then
        echo -e "${RED}Error: Please specify a theme ID${NC}"
        lnmt_theme_list
        return 1
    fi
    
    local theme_file="$THEMES_DIR/${theme_id}.theme"
    
    if [ ! -f "$theme_file" ]; then
        echo -e "${RED}Error: Theme file not found: $theme_file${NC}"
        return 1
    fi
    
    # Source the theme file
    source "$theme_file"
    
    # Save current theme
    echo "$theme_id" > "$CURRENT_THEME_FILE"
    
    echo -e "${GREEN}✅ Theme '$LNMT_ACTIVE_THEME_NAME' loaded successfully${NC}"
    return 0
}

lnmt_theme_info() {
    local theme_id="$1"
    
    if [ -z "$theme_id" ]; then
        echo -e "${RED}Error: Please specify a theme ID${NC}"
        return 1
    fi
    
    local theme_file="$THEMES_DIR/${theme_id}.theme"
    
    if [ ! -f "$theme_file" ]; then
        echo -e "${RED}Error: Theme file not found: $theme_file${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Theme Information:${NC}"
    echo
    grep -E '^THEME_(ID|NAME|AUTHOR|DESCRIPTION|VERSION|TYPE)=' "$theme_file" | while IFS= read -r line; do
        local key=$(echo "$line" | cut -d'=' -f1 | sed 's/THEME_//')
        local value=$(echo "$line" | cut -d'"' -f2)
        printf "  %-12s: %s\\n" "$key" "$value"
    done
}

lnmt_theme_current() {
    if [ -f "$CURRENT_THEME_FILE" ]; then
        local current_theme=$(cat "$CURRENT_THEME_FILE")
        echo -e "${GREEN}Current theme: $current_theme${NC}"
        
        if [ -n "$LNMT_ACTIVE_THEME_NAME" ]; then
            echo -e "${BLUE}Loaded: $LNMT_ACTIVE_THEME_NAME ($LNMT_ACTIVE_THEME_TYPE)${NC}"
        fi
    else
        echo -e "${YELLOW}No theme currently active${NC}"
    fi
}

# Main CLI interface
case "${1:-}" in
    "list"|"ls")
        lnmt_theme_list
        ;;
    "load"|"activate")
        lnmt_theme_load "$2"
        ;;
    "info"|"show")
        lnmt_theme_info "$2"
        ;;
    "current"|"active")
        lnmt_theme_current
        ;;
    *)
        echo -e "${BLUE}LNMT Theme Manager${NC}"
        echo
        echo "Usage: $0 <command> [theme_id]"
        echo
        echo "Commands:"
        echo "  list              - List all available themes"
        echo "  load <theme_id>   - Load and activate a theme"
        echo "  info <theme_id>   - Show theme information"
        echo "  current           - Show currently active theme"
        echo
        echo "Examples:"
        echo "  $0 list"
        echo "  $0 load dark"
        echo "  $0 info solarized"
        ;;
esac'''

    return theme_manager_js, cli_manager

def create_theme_index_json():
    """Create index.json file for theme discovery"""
    
    index_content = {
        "version": "1.0.0",
        "last_updated": "2025-01-01T00:00:00Z",
        "themes": [
            f"{theme_id}.theme" for theme_id in THEMES.keys()
        ],
        "total_themes": len(THEMES)
    }
    
    return json.dumps(index_content, indent=2)

def create_all_theme_files():
    """Create all .theme files and supporting system"""
    print("🚀 Creating LNMT Drop-In Theme System...")
    
    # Create themes directory
    create_themes_directory()
    
    # Generate individual .theme files
    for theme_id, theme_data in THEMES.items():
        theme_content = generate_theme_file(theme_id, theme_data)
        theme_file_path = f"themes/{theme_id}.theme"
        
        with open(theme_file_path, 'w', encoding='utf-8') as f:
            f.write(theme_content)
        
        # Make theme file executable for CLI usage
        os.chmod(theme_file_path, 0o755)
        print(f"✅ Created theme file: {theme_file_path}")
    
    # Create theme management system
    theme_manager_js, cli_manager = create_theme_index_system()
    
    with open("themes/theme-manager.js", 'w', encoding='utf-8') as f:
        f.write(theme_manager_js)
    print("✅ Created theme-manager.js")
    
    with open("themes/theme-manager.sh", 'w', encoding='utf-8') as f:
        f.write(cli_manager)
    os.chmod("themes/theme-manager.sh", 0o755)
    print("✅ Created theme-manager.sh")
    
    # Create theme index
    index_content = create_theme_index_json()
    with open("themes/index.json", 'w', encoding='utf-8') as f:
        f.write(index_content)
    print("✅ Created themes/index.json")
    
    print(f"\\n🎉 Successfully created {len(THEMES)} drop-in .theme files!")
    print("\\n📁 Each .theme file contains:")
    print("   • Theme metadata and colors")
    print("   • Complete CSS for web interface") 
    print("   • Shell functions for CLI interface")
    print("   • Auto-loading and helper functions")
    print("\\n🔧 Usage:")
    print("   Web: Include theme-manager.js and it will auto-index themes/")
    print("   CLI: source themes/dark.theme  # or any theme file")
    print("   Manager: ./themes/theme-manager.sh list")

if __name__ == "__main__":
    create_all_theme_files()
