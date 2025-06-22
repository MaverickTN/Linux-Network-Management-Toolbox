import typer
import json
from pathlib import Path
from inetctl.core.config_loader import load_config, save_config

profile_cli = typer.Typer(
    name="profile",
    help="Manage user profiles and preferences.",
    no_args_is_help=True
)

@profile_cli.command("set-theme")
def set_theme(username: str = typer.Argument(...), theme: str = typer.Argument(...)):
    """
    Set the preferred UI theme for a user.
    """
    config = load_config()
    user_profiles = config.setdefault("user_profiles", {})
    user = user_profiles.setdefault(username, {})
    user["theme"] = theme
    save_config(config)
    typer.echo(f"Theme set to '{theme}' for user '{username}'.")

@profile_cli.command("show")
def show_profile(username: str = typer.Argument(...)):
    """
    Show user profile information and preferences.
    """
    config = load_config()
    user_profiles = config.get("user_profiles", {})
    user = user_profiles.get(username)
    if user:
        typer.echo(json.dumps(user, indent=2))
    else:
        typer.echo(f"User profile for '{username}' not found.")

@profile_cli.command("set-email")
def set_email(
    username: str = typer.Argument(...),
    email: str = typer.Argument(...)
):
    """
    Set an email address for a user.
    """
    config = load_config()
    user_profiles = config.setdefault("user_profiles", {})
    user = user_profiles.setdefault(username, {})
    user["email"] = email
    save_config(config)
    typer.echo(f"Email '{email}' set for user '{username}'.")

@profile_cli.command("set-notifications")
def set_notifications(
    username: str = typer.Argument(...),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable or disable notifications for this user.")
):
    """
    Enable or disable notifications for a user.
    """
    config = load_config()
    user_profiles = config.setdefault("user_profiles", {})
    user = user_profiles.setdefault(username, {})
    user["notifications_enabled"] = enabled
    save_config(config)
    status = "enabled" if enabled else "disabled"
    typer.echo(f"Notifications {status} for user '{username}'.")

# Add more commands here as needed (e.g., password change, add notification channels, etc.)
