# lnmt/main.py

import os
import sys

from lnmt.core.config_loader import load_config
from lnmt.core.theme_manager import apply_theme
from lnmt.web.app import create_app

# Load the active config file
config = load_config()

# Apply the current theme (from config or default)
theme = config.get("theme", "dark")
apply_theme(theme)

# Create Flask app
app = create_app(config=config)

if __name__ == "__main__":
    # For direct invocation (not via lnmt-runner.py)
    port = config.get("web_portal", {}).get("port", 8080)
    app.run(host="0.0.0.0", port=port, debug=config.get("web_portal", {}).get("debug", False))
