# LNMT Theme System Documentation

## Overview

The LNMT (Linux Network Management Toolbox) theme system has been modularized from a single Python file into individual theme files for both web and CLI interfaces. This system provides 10 beautiful themes that work seamlessly across both platforms.

## 🎨 Available Themes

| Theme ID | Name | Type | Description |
|----------|------|------|-------------|
| `dark` | Dark | Dark | Clean dark theme with blue accents |
| `light` | Light | Light | Professional light theme |
| `black` | Blackout | Dark | High contrast black theme with cyan |
| `solarized` | Solarized | Dark | Popular Solarized color scheme |
| `oceanic` | Oceanic | Dark | Ocean-inspired blue theme |
| `nord` | Nord | Dark | Arctic-inspired theme with muted colors |
| `gruvbox` | Gruvbox | Dark | Warm retro groove theme |
| `material` | Material | Dark | Google Material Design colors |
| `retro_terminal` | Retro Terminal | Dark | Classic terminal green on black |
| `matrix` | Green Matrix | Dark | Matrix-inspired green theme |

## 📁 Directory Structure

```
themes/
├── web/
│   ├── themes/           # Individual CSS theme files
│   │   ├── dark.css
│   │   ├── light.css
│   │   ├── black.css
│   │   ├── solarized.css
│   │   ├── oceanic.css
│   │   ├── nord.css
│   │   ├── gruvbox.css
│   │   ├── material.css
│   │   ├── retro_terminal.css
│   │   └── matrix.css
│   └── theme-loader.js   # JavaScript theme manager
├── cli/
│   ├── themes/           # Individual shell theme files
│   │   ├── dark.sh
│   │   ├── light.sh
│   │   ├── black.sh
│   │   ├── solarized.sh
│   │   ├── oceanic.sh
│   │   ├── nord.sh
│   │   ├── gruvbox.sh
│   │   ├── material.sh
│   │   ├── retro_terminal.sh
│   │   └── matrix.sh
│   └── theme-loader.sh   # CLI theme manager
├── manifest.json         # Theme metadata (JSON)
├── manifest.yml          # Theme metadata (YAML)
└── docs/
    ├── README.md         # This file
    ├── migration-guide.md
    └── examples/
        ├── web-integration.html
        └── cli-examples.sh
```

## 🚀 Quick Start

### Installation

1. **Run the theme generator:**
   ```bash
   python3 lnmt_theme_parser.py
   ```

2. **Copy themes to your LNMT installation:**
   ```bash
   cp -r themes/ /path/to/your/lnmt/installation/
   ```

### Web Interface Usage

#### Basic Integration
```html
<!DOCTYPE html>
<html>
<head>
    <title>LNMT Web Interface</title>
    <!-- Load theme manager -->
    <script src="themes/web/theme-loader.js"></script>
</head>
<body>
    <div class="container">
        <h1>Network Management Dashboard</h1>
        
        <!-- Theme selector -->
        <select id="theme-selector" onchange="switchTheme(this.value)">
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="solarized">Solarized</option>
            <option value="matrix">Matrix</option>
        </select>
        
        <!-- Your content -->
        <div class="card">
            <h2 class="primary">System Status</h2>
            <p class="success">All systems operational</p>
            <button class="btn">Refresh</button>
        </div>
    </div>

    <script>
        async function switchTheme(themeId) {
            await window.lnmtThemes.loadTheme(themeId);
        }
        
        // Listen for theme changes
        window.addEventListener('lnmt-theme-changed', (event) => {
            console.log('Theme changed to:', event.detail.themeId);
        });
    </script>
</body>
</html>
```

#### JavaScript API
```javascript
// Initialize theme manager
await window.lnmtThemes.init();

// Load a specific theme
await window.lnmtThemes.loadTheme('solarized');

// Get all available themes
const themes = window.lnmtThemes.getThemes();

// Get current theme
const current = window.lnmtThemes.getCurrentTheme();

// Toggle through themes
await window.lnmtThemes.toggleTheme();

// Get theme information
const themeInfo = window.lnmtThemes.getThemeInfo('nord');
```

### CLI Interface Usage

#### Basic Commands
```bash
# Load the CLI theme loader
source themes/cli/theme-loader.sh

# List available themes
lnmt_theme_load list
# or
./themes/cli/theme-loader.sh list

# Load a theme
lnmt_theme_load load solarized
# or
./themes/cli/theme-loader.sh load solarized

# Show current theme
lnmt_theme_load current

# Get theme information
lnmt_theme_load info matrix

# Reset theme
lnmt_theme_load reset
```

#### Using Theme Functions
```bash
# After loading a theme, you can use these functions:

# Print colored messages
lnmt_print_primary "Primary message"
lnmt_print_success "Operation completed successfully"
lnmt_print_danger "Error occurred"
lnmt_print_warning "Warning message"
lnmt_print_info "Information message"

# Access color variables directly
echo -e "${LNMT_CLI_PRIMARY}This is primary color${LNMT_CLI_RESET}"
echo -e "${LNMT_CLI_SUCCESS}This is success color${LNMT_CLI_RESET}"
```

#### Integration in Scripts
```bash
#!/bin/bash
# Your LNMT script

# Load theme system
source /path/to/themes/cli/theme-loader.sh
lnmt_theme_load load dark > /dev/null 2>&1

# Use themed output
lnmt_print_info "Starting network scan..."
if network_scan_function; then
    lnmt_print_success "Network scan completed"
else
    lnmt_print_danger "Network scan failed"
fi
```

## 🎨 CSS Classes and Variables

### CSS Custom Properties (Web)
Each theme provides these CSS custom properties:

```css
:root {
  --lnmt-primary: #3498db;
  --lnmt-background: #23272e;
  --lnmt-foreground: #e0e0e0;
  --lnmt-accent: #f39c12;
  --lnmt-danger: #e74c3c;
  --lnmt-success: #43a047;
  --lnmt-warning: #ff9800;
  --lnmt-info: #007bff;
  --lnmt-border-radius: 10px;
}
```

### Utility Classes
```css
.theme-{theme-id} .primary   { color: var(--lnmt-primary); }
.theme-{theme-id} .accent    { color: var(--lnmt-accent); }
.theme-{theme-id} .success   { color: var(--lnmt-success); }
.theme-{theme-id} .danger    { color: var(--lnmt-danger); }
.theme-{theme-id} .warning   { color: var(--lnmt-warning); }
.theme-{theme-id} .info      { color: var(--lnmt-info); }
```

### Component Classes
```css
.theme-{theme-id} .btn       { /* Themed button */ }
.theme-{theme-id} .card      { /* Themed card */ }
.theme-{theme-id} .input     { /* Themed input */ }
.theme-{theme-id} .alert-*   { /* Themed alerts */ }
```

## 🖥️ CLI Environment Variables

### ANSI Color Codes
```bash
LNMT_CLI_PRIMARY="\033[94m"     # Primary color
LNMT_CLI_SUCCESS="\033[92m"     # Success color
LNMT_CLI_DANGER="\033[91m"      # Error color
LNMT_CLI_WARNING="\033[93m"     # Warning color
LNMT_CLI_RESET="\033[0m"        # Reset formatting
```

### 256-Color Support
```bash
LNMT_CLI_BACKGROUND="\033[48;2;35;39;46m"  # RGB background
LNMT_CLI_FOREGROUND="\033[38;2;224;224;224m"  # RGB foreground
LNMT_CLI_ACCENT="\033[38;2;243;156;18m"    # RGB accent
```

### Theme Metadata
```bash
LNMT_THEME_NAME="Dark"
LNMT_THEME_ID="dark"
LNMT_THEME_TYPE="dark"
```

## 🔧 Advanced Usage

### Creating Custom Themes

#### 1. Web Theme (CSS)
Create a new CSS file in `themes/web/themes/`:

```css
/**
 * Theme: My Custom Theme
 * ID: custom
 * Type: dark
 * Description: My awesome custom theme
 * Version: 1.0.0
 * Author: Your Name
 */

:root {
  --lnmt-primary: #your-color;
  --lnmt-background: #your-bg;
  --lnmt-foreground: #your-fg;
  --lnmt-accent: #your-accent;
  --lnmt-danger: #your-danger;
  --lnmt-success: #your-success;
  --lnmt-warning: #your-warning;
  --lnmt-info: #your-info;
  --lnmt-border-radius: 8px;
}

.theme-custom {
  background-color: var(--lnmt-background);
  color: var(--lnmt-foreground);
}

/* Add component styles following the pattern */
```

#### 2. CLI Theme (Shell)
Create a new shell file in `themes/cli/themes/`:

```bash
#!/bin/bash
# Theme: My Custom Theme
# ID: custom
# Type: dark
# Description: My awesome custom theme
# Version: 1.0.0
# Author: Your Name

export LNMT_CLI_PRIMARY="\033[your-ansi-code"
export LNMT_CLI_SUCCESS="\033[your-ansi-code"
export LNMT_CLI_DANGER="\033[your-ansi-code"
export LNMT_CLI_WARNING="\033[your-ansi-code"
export LNMT_CLI_RESET="\033[0m"

# Theme functions (copy from existing themes)
lnmt_print_primary() {
    echo -e "${LNMT_CLI_PRIMARY}$1${LNMT_CLI_RESET}"
}
# ... etc
```

#### 3. Update Manifest
Add your theme to `themes/manifest.json`:

```json
{
  "id": "custom",
  "name": "My Custom Theme",
  "type": "dark",
  "description": "My awesome custom theme",
  "version": "1.0.0",
  "files": {
    "web": "web/themes/custom.css",
    "cli": "cli/themes/custom.sh"
  },
  "colors": {
    "primary": "#your-color",
    "background": "#your-bg",
    "foreground": "#your-fg",
    "accent": "#your-accent"
  }
}
```

### Theme Development Tips

1. **Test on Multiple Terminals**: CLI themes may look different across terminal emulators
2. **Accessibility**: Ensure sufficient contrast ratios for readability
3. **Consistency**: Keep similar semantic meanings across themes
4. **Performance**: Minimize CSS specificity for better performance

### Integration with Flask/Django

#### Flask Integration
```python
from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

@app.route('/api/themes')
def get_themes():
    with open('themes/manifest.json', 'r') as f:
        manifest = json.load(f)
    return jsonify(manifest['themes'])

@app.route('/api/themes/<theme_id>')
def get_theme(theme_id):
    with open('themes/manifest.json', 'r') as f:
        manifest = json.load(f)
    
    theme = next((t for t in manifest['themes'] if t['id'] == theme_id), None)
    if theme:
        return jsonify(theme)
    return jsonify({'error': 'Theme not found'}), 404
```

#### Django Integration
```python
# views.py
from django.http import JsonResponse
import json
import os

def get_themes(request):
    manifest_path = os.path.join(settings.BASE_DIR, 'themes', 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    return JsonResponse({'themes': manifest['themes']})

# settings.py
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'themes'),
]
```

## 🔄 Migration Guide

### From Monolithic to Modular

#### Step 1: Backup
```bash
cp themes.py themes.py.backup
```

#### Step 2: Generate New Structure
```bash
python3 lnmt_theme_parser.py
```

#### Step 3: Update Web Code
Replace:
```python
# Old way
from themes import THEMES
theme_data = THEMES['dark']
```

With:
```javascript
// New way
const theme = await window.lnmtThemes.getThemeInfo('dark');
```

#### Step 4: Update CLI Code
Replace:
```python
# Old way
from themes import THEMES
print(f"\033[{THEMES['dark']['cli']['primary']}Primary Text\033[0m")
```

With:
```bash
# New way
source themes/cli/theme-loader.sh
lnmt_theme_load load dark
lnmt_print_primary "Primary Text"
```

#### Step 5: Test Migration
```bash
# Test web themes
python3 -m http.server 8000
# Visit http://localhost:8000/examples/web-integration.html

# Test CLI themes
./themes/cli/theme-loader.sh list
./themes/cli/theme-loader.sh load dark
lnmt_print_success "Migration successful!"
```

## 📊 Theme Comparison

| Feature | Monolithic | Modular |
|---------|------------|---------|
| **File Size** | 1 large file | Multiple small files |
| **Load Time** | All themes loaded | Only active theme loaded |
| **Maintainability** | Difficult | Easy |
| **Sharing** | Entire file | Individual themes |
| **Customization** | Edit main file | Add new files |
| **Version Control** | Single file changes | Granular changes |
| **Performance** | Higher memory usage | Lower memory usage |

## 🛠️ Troubleshooting

### Common Issues

#### Web Themes Not Loading
```javascript
// Check if theme manager is initialized
if (!window.lnmtThemes.initialized) {
    await window.lnmtThemes.init();
}

// Check console for errors
console.log('Available themes:', window.lnmtThemes.getThemes());
```

#### CLI Colors Not Displaying
```bash
# Check terminal support
echo $TERM
echo $COLORTERM

# Test basic colors
echo -e "\033[31mRed\033[0m \033[32mGreen\033[0m \033[34mBlue\033[0m"

# Check if theme is loaded
echo "Current theme: $LNMT_THEME_NAME"
```

#### Manifest Not Found
```bash
# Check file permissions
ls -la themes/manifest.json

# Validate JSON
python3 -m json.tool themes/manifest.json
```

### Performance Optimization

#### Web Optimization
```javascript
// Preload themes
const criticalThemes = ['dark', 'light'];
criticalThemes.forEach(async (themeId) => {
    const link = document.createElement('link');
    link.rel = 'preload';
    link.as = 'style';
    link.href = `/themes/web/themes/${themeId}.css`;
    document.head.appendChild(link);
});
```

#### CLI Optimization
```bash
# Cache theme selection
export LNMT_DEFAULT_THEME="dark"

# Lazy load themes
lnmt_theme_load_lazy() {
    [[ -n "$LNMT_THEME_NAME" ]] || lnmt_theme_load load "$LNMT_DEFAULT_THEME"
}
```

## 📝 Examples

### Complete Web Example
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LNMT Dashboard</title>
    <script src="themes/web/theme-loader.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .theme-selector { padding: 8px 12px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>LNMT Network Dashboard</h1>
            <select id="theme-selector" class="theme-selector">
                <option value="">Select Theme...</option>
            </select>
        </header>
        
        <div class="grid">
            <div class="card">
                <h3 class="primary">System Status</h3>
                <p class="success">✅ All systems operational</p>
                <p class="info">ℹ️ Uptime: 15 days, 3 hours</p>
            </div>
            
            <div class="card">
                <h3 class="primary">Network Traffic</h3>
                <p class="warning">⚠️ High bandwidth usage detected</p>
                <button class="btn">View Details</button>
            </div>
            
            <div class="card">
                <h3 class="primary">Security</h3>
                <p class="danger">❌ 3 failed login attempts</p>
                <button class="btn">Investigate</button>
            </div>
        </div>
    </div>

    <script>
        async function initDashboard() {
            await window.lnmtThemes.init();
            
            const selector = document.getElementById('theme-selector');
            const themes = window.lnmtThemes.getThemes();
            
            themes.forEach(theme => {
                const option = document.createElement('option');
                option.value = theme.id;
                option.textContent = theme.name;
                selector.appendChild(option);
            });
            
            selector.addEventListener('change', async (e) => {
                if (e.target.value) {
                    await window.lnmtThemes.loadTheme(e.target.value);
                }
            });
            
            // Set initial theme
            selector.value = window.lnmtThemes.getCurrentTheme();
        }
        
        document.addEventListener('DOMContentLoaded', initDashboard);
    </script>
</body>
</html>
```

### Complete CLI Example
```bash
#!/bin/bash
# LNMT Network Monitor Script

set -e

# Load theme system
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/themes/cli/theme-loader.sh"

# Load saved theme or default
lnmt_theme_load load "${LNMT_DEFAULT_THEME:-dark}" > /dev/null 2>&1

# Script functions
show_header() {
    echo
    lnmt_print_primary "======================================"
    lnmt_print_primary "  LNMT Network Management Toolbox"
    lnmt_print_primary "======================================"
    echo
}

check_network_status() {
    lnmt_print_info "Checking network status..."
    
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        lnmt_print_success "Internet connectivity: OK"
    else
        lnmt_print_danger "Internet connectivity: FAILED"
    fi
    
    local interfaces=$(ip link show | grep -E '^[0-9]+:' | wc -l)
    lnmt_print_info "Network interfaces: $interfaces"
}

show_bandwidth() {
    lnmt_print_info "Checking bandwidth usage..."
    
    # Simulate bandwidth check
    local usage=$((RANDOM % 100))
    
    if [ $usage -gt 80 ]; then
        lnmt_print_danger "Bandwidth usage: ${usage}% (HIGH)"
    elif [ $usage -gt 60 ]; then
        lnmt_print_warning "Bandwidth usage: ${usage}% (MEDIUM)"
    else
        lnmt_print_success "Bandwidth usage: ${usage}% (NORMAL)"
    fi
}

show_security_status() {
    lnmt_print_info "Checking security status..."
    
    # Simulate security checks
    local failed_logins=$((RANDOM % 5))
    
    if [ $failed_logins -gt 2 ]; then
        lnmt_print_danger "Failed login attempts: $failed_logins (INVESTIGATE)"
    elif [ $failed_logins -gt 0 ]; then
        lnmt_print_warning "Failed login attempts: $failed_logins"
    else
        lnmt_print_success "No suspicious login activity"
    fi
}

show_menu() {
    echo
    lnmt_print_primary "Available Commands:"
    echo "  1) Network Status"
    echo "  2) Bandwidth Usage"
    echo "  3) Security Status"
    echo "  4) Change Theme"
    echo "  5) Exit"
    echo
}

change_theme() {
    echo
    lnmt_print_primary "Available Themes:"
    lnmt_theme_load list
    echo
    read -p "Enter theme name: " theme_name
    
    if lnmt_theme_load load "$theme_name"; then
        lnmt_print_success "Theme changed successfully!"
    else
        lnmt_print_danger "Failed to change theme"
    fi
}

# Main loop
show_header

while true; do
    show_menu
    read -p "Select option (1-5): " choice
    
    case $choice in
        1)
            check_network_status
            ;;
        2)
            show_bandwidth
            ;;
        3)
            show_security_status
            ;;
        4)
            change_theme
            ;;
        5)
            lnmt_print_success "Goodbye!"
            exit 0
            ;;
        *)
            lnmt_print_warning "Invalid option. Please try again."
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done
```

## 🎯 Best Practices

### Theme Development
1. **Consistent Naming**: Use semantic color names (primary, success, danger)
2. **Accessibility**: Maintain WCAG contrast ratios
3. **Testing**: Test themes in different environments
4. **Documentation**: Document custom themes thoroughly

### Performance
1. **Lazy Loading**: Load themes only when needed
2. **Caching**: Cache theme preferences
3. **Minification**: Minify CSS for production
4. **Compression**: Use gzip for theme files

### Maintenance
1. **Version Control**: Track theme changes carefully
2. **Backwards Compatibility**: Support old theme APIs during transition
3. **Testing**: Automated testing for theme functionality
4. **Documentation**: Keep documentation up to date

---

**🎉 Congratulations!** You now have a fully modular theme system for LNMT that works seamlessly across both web and CLI interfaces. The themes are easy to maintain, share, and extend.

For support or contributions, please refer to the LNMT project repository.