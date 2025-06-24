# lnmt/core/theme_manager.py

import json
import os

THEMES_FILE = os.path.join(os.path.dirname(__file__), "../themes.json")

def load_themes():
    if os.path.exists(THEMES_FILE):
        with open(THEMES_FILE, "r") as f:
            return json.load(f)
    # Fallback themes if file not found
    return {
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
            "border-radius": "10px"
        },
        # Add more fallback themes as needed
    }

def get_theme(theme_key="dark"):
    themes = load_themes()
    return themes.get(theme_key, themes["dark"])

def list_theme_names():
    themes = load_themes()
    return {k: v["name"] for k, v in themes.items()}

def theme_css_vars(theme_key="dark"):
    theme = get_theme(theme_key)
    return ":root {\n" + "\n".join([f"  --color-{k}: {v};" for k, v in theme.items()]) + "\n}"

def inject_theme_into_html(html, theme_key="dark"):
    css = theme_css_vars(theme_key)
    return html.replace("<!--THEME_VARS-->", f"<style>{css}</style>")
