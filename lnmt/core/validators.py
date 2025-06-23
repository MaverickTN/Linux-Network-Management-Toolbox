# lnmt/core/validators.py

import jsonschema
import json

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "global_settings": {"type": "object"},
        "system_paths": {"type": "object"},
        "networks": {"type": "array"},
        "known_hosts": {"type": "array"},
        "security": {"type": "object"},
        "web_portal": {"type": "object"},
        "qos_policies": {"type": "object"},
        "pihole": {"type": "object"},
        "wireguard": {"type": "object"}
    },
    "required": [
        "global_settings", "system_paths", "networks", "known_hosts",
        "security", "web_portal", "qos_policies", "pihole", "wireguard"
    ]
}

def validate_config(config):
    try:
        jsonschema.validate(instance=config, schema=CONFIG_SCHEMA)
        return True, ""
    except jsonschema.ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unknown validation error: {e}"

def is_json_valid(json_str):
    try:
        json.loads(json_str)
        return True
    except Exception:
        return False
