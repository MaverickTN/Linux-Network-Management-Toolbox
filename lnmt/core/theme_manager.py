# lnmt/core/theme_manager.py

from lnmt.themes import THEMES

def get_theme(theme_key="dark"):
    """Returns theme dict by key or defaults to dark."""
    return THEMES.get(theme_key, THEMES["dark"])

def list_theme_names():
    """Returns a dict of {key: display name} for all themes."""
    return {k: v["name"] for k, v in THEMES.items()}

def theme_css_vars(theme_key="dark"):
    """Returns CSS :root variables for a selected theme."""
    theme = get_theme(theme_key)
    return ":root {\n" + "\n".join(
        [f"  --color-{k}: {v};" for k, v in theme.items() if not isinstance(v, dict)]
    ) + "\n}"

def cli_color(text, style="primary", theme_key="dark"):
    """Wrap text in CLI color escape codes for the theme."""
    cli_theme = get_theme(theme_key).get("cli", {})
    color = cli_theme.get(style, "")
    reset = cli_theme.get("reset", "")
    return f"{color}{text}{reset}"

def inject_theme_into_html(html, theme_key="dark"):
    """Inserts <style> for theme vars into an HTML template at <!--THEME_VARS--> marker."""
    css = theme_css_vars(theme_key)
    return html.replace("<!--THEME_VARS-->", f"<style>{css}</style>")
