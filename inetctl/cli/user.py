# inetctl/cli/user.py

import typer
import getpass

from inetctl.core.auth import (
    list_allowed_users,
    get_user_role,
    require_role,
    get_theme_for_user,
    prevent_duplicate_web_user,
    auto_create_user_profile
)
from inetctl.theme import list_theme_names

app = typer.Typer(
    name="user",
    help="Manage users and roles for the Linux Network Management Toolbox.",
    no_args_is_help=True
)

@app.command("list")
def list_users():
    """
    List all allowed system users for CLI and their roles.
    """
    users = list_allowed_users()
    typer.echo("Allowed users:")
    for u in users:
        typer.echo(f"  - {u}: {get_user_role(u)}")

@app.command("role")
def show_role(username: str = typer.Option(None, "--username", "-u", help="Show role for a given username (default: current user)")):
    """
    Show the LNMT role for yourself or another user.
    """
    if not username:
        username = getpass.getuser()
    role = get_user_role(username)
    if role:
        typer.echo(f"User '{username}' role: {role}")
    else:
        typer.echo(f"User '{username}' has no LNMT role.")

@app.command("theme")
def show_themes():
    """
    List available themes.
    """
    themes = list_theme_names()
    typer.echo("Available themes:")
    for k, v in themes.items():
        typer.echo(f"  - {k}: {v}")

@app.command("set-theme")
@require_role("operator")
def set_user_theme(
    theme: str = typer.Option(..., "--theme", prompt=True, help="Theme key from available themes")
):
    """
    Set your CLI (and default web) theme. Stored in your LNMT user profile.
    """
    username = getpass.getuser()
    # Simulate saving theme selection (replace with DB/config update)
    # In production, this should update user's profile in the DB
    typer.echo(f"Setting theme for {username} to '{theme}'... (not yet persisted)")

@app.command("notify")
def configure_notifications():
    """
    (Stub) Change notification preferences for yourself.
    """
    username = getpass.getuser()
    # In production: load/save notification options to user profile in DB
    typer.echo(f"Configure notification options for {username}:")
    typer.echo("[TODO] This will be interactive or accept CLI options in a future update.")

@app.command("create-web-profile")
@require_role("admin")
def create_web_profile(username: str):
    """
    Create a web user profile for an allowed system user. Fails if name is a system user.
    """
    if not prevent_duplicate_web_user(username):
        typer.echo(f"Cannot create a web profile for system user '{username}'.")
        raise typer.Exit(code=1)
    auto_create_user_profile(username)
    typer.echo(f"Web profile created for '{username}'.")

@app.command("check")
def check_user():
    """
    Show current user's permissions and theme.
    """
    username = getpass.getuser()
    role = get_user_role(username)
    theme = get_theme_for_user(username)
    typer.echo(f"User: {username}")
    typer.echo(f"Role: {role if role else 'None'}")
    typer.echo(f"Theme: {theme['name']}")

# Add to your Typer CLI group in main.py or inetctl-runner.py as needed.

if __name__ == "__main__":
    app()
