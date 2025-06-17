import os
import yaml

CONFIG_PATH = "/etc/inetctl/config.yaml"
DEFAULT_CONFIG = {
    "app_title": "Linux Network Management Toolbox",
    "site_admin_email": "",
    "theme": "default",
    "other_settings": {}
}

def load_config():
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                loaded = yaml.safe_load(f)
                if loaded:
                    config.update(loaded)
        except Exception as e:
            print(f"Warning: Failed to load config.yaml: {e}")
    return config

def save_config(new_settings):
    try:
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(new_settings, f)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_app_title():
    cfg = load_config()
    return cfg.get("app_title", DEFAULT_CONFIG["app_title"])

def set_app_title(new_title):
    cfg = load_config()
    cfg["app_title"] = new_title
    return save_config(cfg)
