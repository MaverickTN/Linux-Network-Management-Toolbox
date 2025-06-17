import os
import yaml

# Central config path. Adjust here if supporting user/home configs in the future.
CONFIG_PATH = "/etc/inetctl/config.yaml"

DEFAULT_CONFIG = {
    "app_title": "Linux Network Management Toolbox",
    "site_admin_email": "",
    "theme": "default",
    "other_settings": {}
}

def find_config_file():
    """
    Returns the inetctl config path.
    If you add support for per-user config in the future, extend this function.
    """
    return CONFIG_PATH

def load_config():
    """Loads YAML config from CONFIG_PATH, merges with DEFAULT_CONFIG."""
    config = DEFAULT_CONFIG.copy()
    path = find_config_file()
    if os.path.exists(path):
        try:
            with open(path) as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    config.update(loaded)
        except Exception as e:
            print(f"Warning: Failed to load config.yaml: {e}")
    return config

def save_config(new_settings):
    """Save config as YAML to CONFIG_PATH."""
    path = find_config_file()
    try:
        with open(path, "w") as f:
            yaml.safe_dump(new_settings, f)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_app_title():
    """Returns the site/app title for all pages."""
    cfg = load_config()
    return cfg.get("app_title", DEFAULT_CONFIG["app_title"])

def set_app_title(new_title):
    """Sets the app/site title in config."""
    cfg = load_config()
    cfg["app_title"] = new_title
    return save_config(cfg)
