# LNMT Drop-In Theme System 🎨

## Overview

The LNMT Drop-In Theme System provides **single-file themes** that contain both web CSS and CLI shell code in one `.theme` file. Just drop any `.theme` file into your `themes/` folder and it's automatically detected and available for use!

## 🚀 Quick Start

### 1. Generate Theme Files
```bash
python3 lnmt_theme_file_system.py
```

This creates:
```
themes/
├── dark.theme          # Complete dark theme
├── light.theme         # Complete light theme  
├── solarized.theme     # Complete solarized theme
├── matrix.theme        # Complete matrix theme
├── theme-manager.js    # Web theme manager
├── theme-manager.sh    # CLI theme manager
└── index.json          # Theme index for auto-discovery
```

### 2. Web Usage
```html
<!DOCTYPE html>
<html>
<head>
    <title>My LNMT App</title>
    <!-- Include the theme manager -->
    <script src="themes/theme-manager.js"></script>
</head>
<body>
    <!-- Theme selector (auto-populated) -->
    <select id="theme-selector"></select>
    
    <!-- Your content with theme classes -->
    <div class="card">
        <h2 class="text-primary">Network Status</h2>
        <p class="text-success">All systems operational</p>
        <button class="btn">Refresh</button>
    </div>
    
    <script>
        // Initialize theme system
        window.lnmtThemes.then(manager => {
            // Populate theme selector
            manager.populateSelector(document.getElementById('theme-selector'));
            
            // Handle theme changes
            document.getElementById('theme-selector').addEventListener('change', (e) => {
                if (e.target.value) {
                    manager.applyTheme(e.target.value);
                }
            });
        });
    </script>
</body>
</html>
```

### 3. CLI Usage
```bash
# List available themes
./themes/theme-manager.sh list

# Load a theme
source themes/dark.theme

# Use theme functions
lnmt_print_success "Connected to network"
lnmt_banner "System Status" 
lnmt_test_cli_colors
```

## 📁 Theme File Structure

Each `.theme` file is self-contained and includes:

```bash
#!/usr/bin/env lnmt-theme
# LNMT Theme File - Dark

# === THEME METADATA ===
THEME_ID="dark"
THEME_NAME="Dark"
THEME_AUTHOR="LNMT Team"
THEME_DESCRIPTION="Clean dark theme with blue accents"
THEME_VERSION="1.0.0"
THEME_TYPE="dark"

# === COLOR PALETTE ===
PRIMARY="#3498db"
BACKGROUND="#23272e"
FOREGROUND="#e0e0e0"
# ... more colors

# === WEB CSS (Embedded) ===
read -r -d '' THEME_WEB_CSS << 'EOF_CSS'
.lnmt-theme-dark {
  --primary: #3498db;
  --background: #23272e;
  /* ... complete CSS */
}
EOF_CSS

# === CLI SHELL COLORS (Embedded) ===
export LNMT_CLI_PRIMARY="\033[94m"
export LNMT_CLI_SUCCESS="\033[92m"
# ... more ANSI colors

# === HELPER FUNCTIONS ===
lnmt_print_primary() { echo -e "${LNMT_CLI_PRIMARY}$1${LNMT_CLI_RESET}"; }
lnmt_print_success() { echo -e "${LNMT_CLI_SUCCESS}✅ $1${LNMT_CLI_RESET}"; }
# ... more functions
```

## 🎯 Key Features

### ✅ **Drop-In Ready**
- Single file contains everything needed
- No compilation or build process required
- Auto-detected when placed in `themes/` folder
- Instant theme switching

### ✅ **Cross-Platform Pairing**
- Web CSS and CLI colors perfectly paired
- Consistent branding across interfaces
- ANSI and true color support
- Helper functions included

### ✅ **Easy Distribution**
- Share single `.theme` file
- Version metadata embedded
- Author attribution included
- Self-documenting format

### ✅ **Auto-Indexing**
- Theme manager scans `themes/` folder
- Automatically populates theme selectors
- No manual registration required
- Dynamic theme discovery

## 🔧 Advanced Usage

### Creating Custom Themes

1. **Copy an existing theme:**
   ```bash
   cp themes/dark.theme themes/mytheme.theme
   ```

2. **Edit the metadata:**
   ```bash
   # Change these values in your new theme file
   THEME_ID="mytheme"
   THEME_NAME="My Custom Theme"
   THEME_AUTHOR="Your Name"
   THEME_DESCRIPTION="My awesome custom theme"
   ```

3. **Update the colors:**
   ```bash
   PRIMARY="#your-color"
   BACKGROUND="#your-bg"
   FOREGROUND="#your-fg"
   # ... etc
   ```

4. **The CSS and shell colors are automatically generated from these values!**

### Web Integration

```javascript
// Advanced theme management
class MyApp {
    async init() {
        // Wait for theme manager to load
        const themeManager = await window.lnmtThemes;
        
        // Get all available themes
        const themes = themeManager.getThemes();
        console.log('Available themes:', themes);
        
        // Listen for theme changes
        window.addEventListener('lnmt-theme-changed', (event) => {
            console.log('Theme changed to:', event.detail.themeId);
            this.onThemeChanged(event.detail.theme);
        });
        
        // Apply saved theme or default
        const savedTheme = localStorage.getItem('my-app-theme') || 'dark';
        await themeManager.applyTheme(savedTheme);
    }
    
    onThemeChanged(theme) {
        // Update your app's theme-specific logic
        this.updateChartColors(theme.colors);
        this.updateMapStyle(theme.type);
    }
}
```

### CLI Integration

```bash
#!/bin/bash
# Your LNMT script with theme support

# Load saved theme or default
DEFAULT_THEME="${LNMT_DEFAULT_THEME:-dark}"
if [ -f "themes/${DEFAULT_THEME}.theme" ]; then
    source "themes/${DEFAULT_THEME}.theme"
else
    echo "Warning: Theme not found, using fallback colors"
fi

# Use theme functions in your script
show_status() {
    lnmt_banner "Network Monitor"
    
    if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
        lnmt_print_success "Internet connectivity: OK"
    else
        lnmt_print_danger "Internet connectivity: FAILED"
    fi
    
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    lnmt_print_info "System load: $load_avg"
}

# Theme switching in CLI
switch_theme() {
    echo "Available themes:"
    ls themes/*.theme | sed 's/themes\///g' | sed 's/\.theme//g' | nl
    
    read -p "Select theme number: " choice
    theme_file=$(ls themes/*.theme | sed -n "${choice}p")
    
    if [ -f "$theme_file" ]; then
        source "$theme_file"
        lnmt_print_success "Theme switched to $LNMT_ACTIVE_THEME_NAME"
        echo "$LNMT_ACTIVE_THEME" > ~/.lnmt_theme
    fi
}
```

## 📊 Theme File Format Reference

### Metadata Section
```bash
THEME_ID="unique_id"           # Unique identifier
THEME_NAME="Display Name"      # Human-readable name
THEME_AUTHOR="Author Name"     # Theme creator
THEME_DESCRIPTION="..."        # Brief description
THEME_VERSION="1.0.0"          # Version number
THEME_TYPE="dark|light"        # Theme type
```

### Color Palette
```bash
PRIMARY="#hex"                 # Primary brand color
BACKGROUND="#hex"              # Main background
FOREGROUND="#hex"              # Main text color
ACCENT="#hex"                  # Accent/highlight color
SUCCESS="#hex"                 # Success state color
DANGER="#hex"                  # Error/danger color
WARNING="#hex"                 # Warning state color
INFO="#hex"                    # Information color
BORDER_RADIUS="value"          # Border radius for UI elements
```

### Embedded CSS
```bash
read -r -d '' THEME_WEB_CSS << 'EOF_CSS'
/* Your complete CSS here */
.lnmt-theme-{id} {
  /* CSS custom properties and styles */
}
EOF_CSS
```

### CLI Color Exports
```bash
export LNMT_CLI_PRIMARY="\033[94m"
export LNMT_CLI_SUCCESS="\033[92m"
export LNMT_CLI_DANGER="\033[91m"
export LNMT_CLI_WARNING="\033[93m"
export LNMT_CLI_RESET="\033[0m"
```

### Helper Functions
```bash
lnmt_print_primary()    # Print primary colored text
lnmt_print_success()    # Print success message with ✅
lnmt_print_danger()     # Print error message with ❌
lnmt_print_warning()    # Print warning message with ⚠️
lnmt_print_info()       # Print info message with ℹ️
lnmt_banner()           # Print decorative banner
lnmt_test_cli_colors()  # Test all CLI colors
lnmt_get_theme_info()   # Print theme information
```

## 🛠️ CLI Commands

### Theme Manager Commands
```bash
# List all available themes
./themes/theme-manager.sh list

# Load/activate a theme
./themes/theme-manager.sh load dark

# Show theme information
./themes/theme-manager.sh info solarized

# Show currently active theme
./themes/theme-manager.sh current
```

### Direct Theme Usage
```bash
# Source a theme directly
source themes/dark.theme

# Test the theme colors
lnmt_test_cli_colors

# Get theme information
lnmt_get_theme_info

# Use in your scripts
lnmt_print_success "Operation completed successfully"
lnmt_banner "System Status"
```

## 🌐 Web API Reference

### Theme Manager Class
```javascript
window.lnmtThemes  // Promise that resolves to LNMTThemeManager instance

// Methods
await manager.indexThemes()           // Scan and index themes
await manager.applyTheme(themeId)     // Apply a theme
manager.getThemes()                   // Get all themes array
manager.getTheme(themeId)             // Get specific theme info
manager.populateSelector(element)     // Populate <select> element
```

### Events
```javascript
// Theme change event
window.addEventListener('lnmt-theme-changed', (event) => {
    const { themeId, theme } = event.detail;
    console.log(`Theme changed to: ${theme.name}`);
});
```

### CSS Classes Available in Themes
```css
.lnmt-theme-{id}           /* Main theme container */
.btn                       /* Themed buttons */
.card                      /* Themed cards */
.input                     /* Themed inputs */
.alert                     /* Alert containers */ 
.alert-success             /* Success alerts */
.alert-danger              /* Error alerts */
.alert-warning             /* Warning alerts */
.alert-info                /* Info alerts */
.text-primary              /* Primary text color */
.text-success              /* Success text color */
.text-danger               /* Danger text color */
.text-warning              