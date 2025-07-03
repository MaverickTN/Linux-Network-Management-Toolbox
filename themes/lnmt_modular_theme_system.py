#!/usr/bin/env python3
"""
LNMT Modular Theme System - Paired Structure
Creates self-contained theme modules with web/CLI components paired together
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

def create_modular_structure():
    """Create the modular directory structure"""
    base_directories = [
        "themes",
        "themes/core"
    ]
    
    # Create individual theme directories
    for theme_id in THEMES.keys():
        theme_directories = [
            f"themes/{theme_id}",
            f"themes/{theme_id}/web",
            f"themes/{theme_id}/cli"
        ]
        base_directories.extend(theme_directories)
    
    for directory in base_directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Created modular directory structure")

def generate_theme_metadata(theme_id, theme_data):
    """Generate metadata file for a theme"""
    theme_type = "dark" if is_dark_theme(theme_data) else "light"
    
    metadata = {
        "id": theme_id,
        "name": theme_data['name'],
        "version": "1.0.0",
        "type": theme_type,
        "description": f"LNMT {theme_data['name']} theme with web and CLI support",
        "author": "LNMT Project",
        "keywords": [theme_type, "terminal", "web", "network-management"],
        "colors": {
            "primary": theme_data['primary'],
            "background": theme_data['background'],
            "foreground": theme_data['foreground'],
            "accent": theme_data['accent'],
            "danger": theme_data['danger'],
            "success": theme_data['success'],
            "warning": theme_data['warning'],
            "info": theme_data['info']
        },
        "styling": {
            "border_radius": theme_data['border-radius']
        },
        "platforms": {
            "web": {
                "css_file": "web/style.css",
                "js_file": "web/theme.js",
                "support": ["chrome", "firefox", "safari", "edge"]
            },
            "cli": {
                "shell_file": "cli/colors.sh",
                "support": ["bash", "zsh", "fish"],
                "features": ["ansi_colors", "256_colors", "true_colors"]
            }
        },
        "compatibility": {
            "lnmt_version": ">=1.0.0",
            "web_browsers": ["modern"],
            "terminals": ["xterm", "gnome-terminal", "iterm2", "windows-terminal"]
        }
    }
    
    return metadata

def generate_theme_css(theme_id, theme_data):
    """Generate CSS file for a theme module"""
    theme_type = "dark" if is_dark_theme(theme_data) else "light"
    
    css_content = f"""/**
 * LNMT Theme: {theme_data['name']}
 * ID: {theme_id}
 * Type: {theme_type}
 * Version: 1.0.0
 * 
 * This CSS file is part of the {theme_data['name']} theme module.
 * It provides all styling for the LNMT web interface.
 */

/* Theme Root Variables */
:root.theme-{theme_id} {{
  /* Base Colors */
  --lnmt-bg-primary: {theme_data['background']};
  --lnmt-bg-secondary: {adjust_color(theme_data['background'], 0.05)};
  --lnmt-fg-primary: {theme_data['foreground']};
  --lnmt-fg-secondary: {adjust_color(theme_data['foreground'], -0.2)};
  
  /* Brand Colors */
  --lnmt-primary: {theme_data['primary']};
  --lnmt-primary-hover: {adjust_color(theme_data['primary'], 0.1)};
  --lnmt-accent: {theme_data['accent']};
  --lnmt-accent-hover: {adjust_color(theme_data['accent'], 0.1)};
  
  /* Status Colors */
  --lnmt-success: {theme_data['success']};
  --lnmt-success-bg: {theme_data['success']}20;
  --lnmt-danger: {theme_data['danger']};
  --lnmt-danger-bg: {theme_data['danger']}20;
  --lnmt-warning: {theme_data['warning']};
  --lnmt-warning-bg: {theme_data['warning']}20;
  --lnmt-info: {theme_data['info']};
  --lnmt-info-bg: {theme_data['info']}20;
  
  /* Layout */
  --lnmt-border-radius: {theme_data['border-radius']};
  --lnmt-border-color: {theme_data['primary']}40;
  --lnmt-shadow: 0 2px 8px {theme_data['background']}80;
  
  /* Typography */
  --lnmt-font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  --lnmt-font-mono: 'Courier New', 'Monaco', 'Menlo', monospace;
}}

/* Base Theme Application */
.lnmt-theme-{theme_id} {{
  background-color: var(--lnmt-bg-primary);
  color: var(--lnmt-fg-primary);
  font-family: var(--lnmt-font-family);
  transition: all 0.3s ease;
}}

/* Component Styles */
.lnmt-theme-{theme_id} .lnmt-card {{
  background: var(--lnmt-bg-secondary);
  border: 1px solid var(--lnmt-border-color);
  border-radius: var(--lnmt-border-radius);
  padding: 1.5rem;
  margin: 1rem 0;
  box-shadow: var(--lnmt-shadow);
  transition: all 0.3s ease;
}}

.lnmt-theme-{theme_id} .lnmt-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 16px {theme_data['background']}40;
}}

.lnmt-theme-{theme_id} .lnmt-btn {{
  background: var(--lnmt-primary);
  color: var(--lnmt-bg-primary);
  border: 2px solid var(--lnmt-primary);
  border-radius: var(--lnmt-border-radius);
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}}

.lnmt-theme-{theme_id} .lnmt-btn:hover {{
  background: var(--lnmt-primary-hover);
  border-color: var(--lnmt-primary-hover);
  transform: translateY(-1px);
}}

.lnmt-theme-{theme_id} .lnmt-btn-outline {{
  background: transparent;
  color: var(--lnmt-primary);
  border: 2px solid var(--lnmt-primary);
}}

.lnmt-theme-{theme_id} .lnmt-btn-outline:hover {{
  background: var(--lnmt-primary);
  color: var(--lnmt-bg-primary);
}}

.lnmt-theme-{theme_id} .lnmt-input {{
  background: var(--lnmt-bg-secondary);
  border: 2px solid var(--lnmt-border-color);
  border-radius: var(--lnmt-border-radius);
  color: var(--lnmt-fg-primary);
  padding: 0.75rem 1rem;
  font-size: 1rem;
  transition: all 0.3s ease;
  width: 100%;
}}

.lnmt-theme-{theme_id} .lnmt-input:focus {{
  outline: none;
  border-color: var(--lnmt-primary);
  box-shadow: 0 0 0 3px var(--lnmt-primary)20;
}}

/* Status Components */
.lnmt-theme-{theme_id} .lnmt-alert {{
  padding: 1rem 1.5rem;
  border-radius: var(--lnmt-border-radius);
  border-left: 4px solid;
  margin: 1rem 0;
}}

.lnmt-theme-{theme_id} .lnmt-alert-success {{
  background: var(--lnmt-success-bg);
  border-color: var(--lnmt-success);
  color: var(--lnmt-success);
}}

.lnmt-theme-{theme_id} .lnmt-alert-danger {{
  background: var(--lnmt-danger-bg);
  border-color: var(--lnmt-danger);
  color: var(--lnmt-danger);
}}

.lnmt-theme-{theme_id} .lnmt-alert-warning {{
  background: var(--lnmt-warning-bg);
  border-color: var(--lnmt-warning);
  color: var(--lnmt-warning);
}}

.lnmt-theme-{theme_id} .lnmt-alert-info {{
  background: var(--lnmt-info-bg);
  border-color: var(--lnmt-info);
  color