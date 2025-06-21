# inetctl/cli/profile.py

import typer
import os
import getpass
from inetctl.core.user_profile import (
    get_user_profile,
    update_user_profile,
    get_theme_names,
)
from inetctl.core.auth import check_user_group, current_cli_user, LNMT_GROUPS
from inetctl.theme import cli_color

app = typer.Typer(
    name="profile",
    help="Manage your Linux Network Management Toolbox user profile.",
    no_args_is_help=True,
)

def ensure_group_access():
    user = current_cli_user()
    group = check_user_group(user)
    if group not in LNMT_GROUPS:
        typer.secho("You do not have permission to access the profile CLI. Membership in lnmtadm, lnmt, or lnmtv required.", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command("show")
def show_profile():
    """Show current user's profile."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    typer.echo(cli_color(f"\nUser Profile for {profile['username']}\n", "primary", profile.get("theme", "dark")))
    for k, v in profile.items():
        if k == "notification_settings":
            typer.echo(cli_color("Notifications:", "info", profile.get("theme", "dark")))
            for event, enabled in v.items():
                typer.echo(f"  {event}: {'Enabled' if enabled else 'Disabled'}")
        else:
            typer.echo(f"{k}: {v}")

@app.command("set-theme")
def set_theme(
    theme: str = typer.Option(..., prompt=True, help="Theme key to use. Run 'profile list-themes' to see available.")
):
    """Set CLI and web theme for your profile."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    all_themes = get_theme_names()
    if theme not in all_themes:
        typer.echo(cli_color(f"Theme '{theme}' is not available. Choose from: {', '.join(all_themes)}", "danger", profile.get("theme", "dark")))
        raise typer.Exit(1)
    update_user_profile(profile['username'], {"theme": theme})
    typer.echo(cli_color(f"Theme changed to {all_themes[theme]}.", "success", theme))

@app.command("set-notifications")
def set_notifications(
    event: str = typer.Option(..., help="Event key (e.g., 'job_complete')"),
    enabled: bool = typer.Option(..., help="Enable (True) or disable (False)")
):
    """Enable or disable notification for a specific event."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    notifications = profile.get("notification_settings", {})
    if event not in notifications:
        typer.echo(cli_color(f"Unknown event '{event}'.", "danger", profile.get("theme", "dark")))
        raise typer.Exit(1)
    notifications[event] = enabled
    update_user_profile(profile['username'], {"notification_settings": notifications})
    typer.echo(cli_color(f"Notification for '{event}' set to {'Enabled' if enabled else 'Disabled'}.", "success", profile.get("theme", "dark")))

@app.command("change-password")
def change_password():
    """Change your account password (will use PAM if available)."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    pw1 = getpass.getpass("Enter new password: ")
    pw2 = getpass.getpass("Confirm new password: ")
    if pw1 != pw2:
        typer.echo(cli_color("Passwords do not match.", "danger", profile.get("theme", "dark")))
        raise typer.Exit(1)
    result = update_user_profile(profile['username'], {"new_password": pw1})
    if result.get("success"):
        typer.echo(cli_color("Password updated successfully.", "success", profile.get("theme", "dark")))
    else:
        typer.echo(cli_color(f"Password update failed: {result.get('message')}", "danger", profile.get("theme", "dark")))

@app.command("set-email")
def set_email(
    email: str = typer.Option(..., prompt=True, help="Email address for notifications")
):
    """Set or update your email address."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    result = update_user_profile(profile['username'], {"email": email})
    if result.get("success"):
        typer.echo(cli_color("Email updated.", "success", profile.get("theme", "dark")))
    else:
        typer.echo(cli_color("Failed to update email.", "danger", profile.get("theme", "dark")))

@app.command("list-themes")
def list_themes():
    """Show all available theme keys and names."""
    ensure_group_access()
    themes = get_theme_names()
    typer.echo(cli_color("\nAvailable Themes:", "primary"))
    for k, v in themes.items():
        typer.echo(f"  {k}: {v}")

# Menu mode
@app.command("menu")
def menu():
    """Menu-driven profile editor."""
    ensure_group_access()
    profile = get_user_profile(current_cli_user())
    theme = profile.get("theme", "dark")
    while True:
        typer.echo(cli_color("\n--- User Profile Menu ---", "primary", theme))
        typer.echo("1. Show Profile")
        typer.echo("2. Change Theme")
        typer.echo("3. Change Password")
        typer.echo("4. Set Email")
        typer.echo("5. Set Notification")
        typer.echo("6. List Themes")
        typer.echo("0. Exit")
        choice = typer.prompt("Select an option")
        if choice == "1":
            show_profile()
        elif choice == "2":
            list_themes()
            t = typer.prompt("Enter theme key")
            set_theme(t)
        elif choice == "3":
            change_password()
        elif choice == "4":
            e = typer.prompt("Enter new email")
            set_email(e)
        elif choice == "5":
            ev = typer.prompt("Enter event name (e.g., job_complete)")
            en = typer.confirm("Enable?")
            set_notifications(ev, en)
        elif choice == "6":
            list_themes()
        elif choice == "0":
            break
        else:
            typer.echo(cli_color("Invalid option.", "danger", theme))

if __name__ == "__main__":
    app()
