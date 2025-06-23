import typer
from typing import Optional, List
import getpass

from lnmt.core.user import (
    get_user_profile,
    save_user_profile,
    list_profiles,
    create_profile_for_host_user,
    remove_user_profile,
    user_groups,
    valid_group_for_cli,
    is_valid_new_user,
    set_user_theme,
    update_user_email,
    update_user_notify,
    pam_authenticate,
    ensure_profiles_for_group_users,
)
from lnmt.theme import list_theme_names

cli = typer.Typer(
    name="user",
    help="Manage LNMT user profiles, themes, and notification settings.",
    no_args_is_help=True
)

@cli.command("list")
def list_users():
    """List all LNMT user profiles."""
    profiles = list_profiles()
    if not profiles:
        typer.echo("No user profiles found.")
        return
    typer.echo("LNMT User Profiles:\n-------------------")
    for p in profiles:
        typer.echo(f"{p['username']} | theme: {p.get('theme','dark')}, email: {p.get('email','-')}, notify: {','.join(p.get('notify',[]))}")

@cli.command("create")
def create_user(
    username: str = typer.Argument(..., help="Username (must not match a host user)"),
    theme: str = typer.Option("dark", "--theme", "-t", help="Initial theme"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address"),
    notify: List[str] = typer.Option([], "--notify", "-n", help="Notification event types")
):
    """
    Create a new LNMT user profile (for web-only users).
    """
    if not is_valid_new_user(username):
        typer.echo(f"Cannot create: Username '{username}' matches a system account.")
        raise typer.Exit(1)
    if get_user_profile(username):
        typer.echo(f"Profile for '{username}' already exists.")
        raise typer.Exit(1)
    profile = {
        "username": username,
        "theme": theme,
        "email": email or "",
        "notify": list(notify),
        "auth_source": "local"
    }
    save_user_profile(profile)
    typer.echo(f"User profile created for '{username}'.")

@cli.command("sync-host")
def sync_host_users():
    """
    Auto-create LNMT profiles for all host users in valid LNMT CLI groups.
    """
    ensure_profiles_for_group_users()
    typer.echo("Host-group user sync complete. Profiles updated.")

@cli.command("remove")
def remove_user(
    username: str = typer.Argument(..., help="Username of profile to remove")
):
    """
    Remove an LNMT user profile.
    """
    if not get_user_profile(username):
        typer.echo(f"No such user profile: {username}")
        raise typer.Exit(1)
    remove_user_profile(username)
    typer.echo(f"Removed user profile: {username}")

@cli.command("theme")
def change_theme(
    username: str = typer.Argument(..., help="Username"),
    theme: str = typer.Argument(..., help="Theme key (see --list)"),
    list_: bool = typer.Option(False, "--list", "-l", help="List available themes"),
):
    """
    Change a user's preferred theme.
    """
    if list_:
        for k, v in list_theme_names().items():
            typer.echo(f"{k}: {v}")
        raise typer.Exit(0)
    set_user_theme(username, theme)
    typer.echo(f"Theme for '{username}' set to {theme}.")

@cli.command("email")
def set_email(
    username: str = typer.Argument(..., help="Username"),
    email: str = typer.Argument(..., help="Email address")
):
    """
    Set the user's email address.
    """
    update_user_email(username, email)
    typer.echo(f"Email for '{username}' set to {email}.")

@cli.command("notify")
def set_notify(
    username: str = typer.Argument(..., help="Username"),
    notify: List[str] = typer.Option([], "--event", "-e", help="Event type (repeatable)")
):
    """
    Set notification events for user (replaces all current).
    """
    update_user_notify(username, notify)
    typer.echo(f"Notify events for '{username}' set: {', '.join(notify)}")

@cli.command("show")
def show_user(
    username: str = typer.Argument(..., help="Username")
):
    """Show details for a user profile."""
    profile = get_user_profile(username)
    if not profile:
        typer.echo(f"No profile found for '{username}'.")
        raise typer.Exit(1)
    typer.echo(f"Profile for '{username}':\n" + "-"*30)
    for k, v in profile.items():
        typer.echo(f"{k}: {v}")

@cli.command("groups")
def list_user_groups(
    username: str = typer.Argument(..., help="Username")
):
    """List host groups for a user."""
    groups = user_groups(username)
    if not groups:
        typer.echo(f"No groups found for '{username}'.")
        raise typer.Exit(1)
    typer.echo(f"Groups for '{username}': " + ", ".join(groups))

@cli.command("test-pam")
def test_pam_auth(
    username: str = typer.Argument(..., help="System username"),
):
    """Test PAM authentication for a user."""
    password = getpass.getpass("Password: ")
    if pam_authenticate(username, password):
        typer.echo("PAM authentication succeeded!")
    else:
        typer.echo("PAM authentication failed.")

@cli.command("check-cli")
def check_cli_allowed(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Check CLI access for this username (defaults to current user)")
):
    """
    Check if user has CLI permission (via group).
    """
    import os
    if not username:
        username = os.getlogin()
    if valid_group_for_cli(username):
        typer.echo(f"User '{username}' is permitted CLI access.")
    else:
        typer.echo(f"User '{username}' is NOT permitted CLI access.")

if __name__ == "__main__":
    cli()
