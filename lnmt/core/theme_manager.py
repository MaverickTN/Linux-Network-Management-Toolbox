# lnmt/core/theme_manager.py

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

def get_theme(theme_key="dark"):
    return THEMES.get(theme_key, THEMES["dark"])

def list_theme_names():
    return {k: v["name"] for k, v in THEMES.items()}

def theme_css_vars(theme_key="dark"):
    theme = get_theme(theme_key)
    return ":root {\n" + "\n".join([f"  --color-{k}: {v};" for k, v in theme.items() if k != "cli" and k != "name"]) + "\n}"

def cli_color(text, style="primary", theme_key="dark"):
    return f"{THEMES.get(theme_key, THEMES['dark'])['cli'].get(style, '')}{text}{THEMES[theme_key]['cli']['reset']}"

def inject_theme_into_html(html, theme_key="dark"):
    css = theme_css_vars(theme_key)
    return html.replace("<!--THEME_VARS-->", f"<style>{css}</style>")
