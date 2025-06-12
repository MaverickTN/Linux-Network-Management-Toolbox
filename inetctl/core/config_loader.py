import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import typer

# --- Global Configuration Variables ---
APP_CONFIG: Optional[Dict[str, Any]] = None
LOADED_CONFIG_PATH: Optional[Path] = None


def find_config_file() -> Optional[Path]:
    """Tries to find the configuration file in predefined locations."""
    env_path_str = os.environ.get("INETCTL_CONFIG")
    if env_path_str:
        env_path = Path(env_path_str)
        if env_path.exists() and env_path.is_file():
            return env_path.resolve()
        else:
            typer.echo(typer.style(f"Error: INETCTL_CONFIG set to '{env_path_str}' but file not found.", fg=typer.colors.RED, bold=True))
            raise typer.Exit(code=1)

    current_dir_config_path = Path("./server_config.json")
    home_config_path = Path.home() / ".config" / "inetctl" / "server_config.json"

    if current_dir_config_path.exists() and current_dir_config_path.is_file():
        return current_dir_config_path.resolve()
    if home_config_path.exists() and home_config_path.is_file():
        return home_config_path.resolve()
        
    return None

def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """Loads the configuration file. Caches after first load unless force_reload is True."""
    global APP_CONFIG, LOADED_CONFIG_PATH

    is_init_command = "config" in sys.argv and "init" in sys.argv
    is_web_command = "web" in sys.argv

    if APP_CONFIG is not None and not force_reload:
        return APP_CONFIG

    config_path = find_config_file()
    
    if not config_path:
        if is_init_command or is_web_command:
            return {}
        typer.echo(typer.style("Error: 'server_config.json' not found. Run 'inetctl config init' first.", fg=typer.colors.RED, bold=True))
        raise typer.Exit(code=1)

    LOADED_CONFIG_PATH = config_path

    try:
        with open(config_path, "r") as f:
            APP_CONFIG = json.load(f)
        if not isinstance(APP_CONFIG, dict): 
            raise ValueError("Configuration root must be a JSON object.")
            
    except Exception as e:
        typer.echo(typer.style(f"Error loading configuration from {config_path}: {e}", fg=typer.colors.RED, bold=True))
        APP_CONFIG = None
        raise typer.Exit(code=1)
        
    return APP_CONFIG

def save_config(config_data: Dict[str, Any], path_override: Optional[Path] = None) -> bool:
    """Safely saves the provided configuration data."""
    global APP_CONFIG, LOADED_CONFIG_PATH
    
    save_path = path_override or LOADED_CONFIG_PATH
    
    if not save_path:
        typer.echo(typer.style("Error: Cannot save configuration, file path is unknown.", fg=typer.colors.RED, bold=True))
        return False

    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path_str = tempfile.mkstemp(dir=str(save_path.parent))
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(config_data, tmp_file, indent=2)
            tmp_file.write('\n')
        
        os.replace(temp_path_str, str(save_path))
        
        if not path_override:
            APP_CONFIG = config_data
        
        if "web" not in sys.argv:
            typer.echo(typer.style(f"Successfully saved configuration to {save_path}", fg=typer.colors.GREEN))
        return True
    except Exception as e:
        typer.echo(typer.style(f"Error saving configuration to {save_path}: {e}", fg=typer.colors.RED, bold=True))
        if 'temp_path_str' in locals() and Path(temp_path_str).exists():
            try: Path(temp_path_str).unlink()
            except OSError: pass
        return False
