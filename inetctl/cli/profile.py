import typer
from pathlib import Path
import getpass
import pwd
import grp
from inetctl.core import profile as profile_core
from inetctl.theme import list_theme_names

cli = typer.Typer(help="Manage user profiles and preferences.")

def _require_host_user(username):
    """Raise if username does not exist on the host."""
    try:
        pwd.getpwnam(username)
    except KeyError:
        typer.echo(typer.style(f"User '{username}' does not exist on this system.", fg=typer.colors.RED), err=True)
        raise typer.Exit(1)

def _check_group_access(username, allowed=("lnmtadm", "lnmt", "lnmtv")):
    """Return access_level or exit."""
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    # Primary group also matters
    try:
        primary_gid = pwd.getpwnam(username).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        if primary_group not in groups:
            groups.append(primary_group)
    except Exception:
        pass
    for level, group in (("admin", "lnmtadm"), ("operator", "lnmt"), ("viewer", "lnmtv")):
        if group in groups:
            return level
    typer.echo(typer.style("User does not have LNMT CLI permissions.", fg=typer.colors.RED), err=True)
    raise typer.Exit(1)

@cli.command()
def list_users():
    """List all profiles (local only)."""
    users = profile_core.list_user_profiles()
    if not users:
        typer.echo("No user profiles found.")
        raise typer.Exit()
    typer.echo("User profiles:")
    for u in users:
        typer.echo(f"- {u}")

@cli.command()
def show(username: str = typer.Argument(..., help="Username to display")):
    """Show user profile data."""
    _require_host_user(username)
    profile = profile_core.get_user_profile(username)
    typer.echo(profile)

@cli.command()
def create(
    username: str = typer.Argument(..., help="Host system username"),
    email: str = typer.Option("", help="User's email"),
    display_name: str = typer.Option("", help="Display name"),
    theme: str = typer.Option("dark", help="Theme"),
):
    """Create a new user profile for a system user."""
    _require_host_user(username)
    if profile_core.user_profile_exists(username):
        typer.echo(f"Profile already exists for {username}")
        raise typer.Exit(1)
    level = _check_group_access(username)
    profile_core.create_user_profile(
        username=username,
        email=email,
        display_name=display_name,
        theme=theme,
        access_level=level
    )
    typer.echo(f"Created profile for {username} (access: {level})")

@cli.command()
def update(
    username: str = typer.Argument(..., help="Username to update"),
    theme: str = typer.Option(None, help="Theme"),
    email: str = typer.Option(None, help="Email"),
    display_name: str = typer.Option(None, help="Display name"),
    notif_network: bool = typer.Option(None, help="Network event notifications"),
    notif_config: bool = typer.Option(None, help="Config change notifications"),
    notif_security: bool = typer.Option(None, help="Security alert notifications"),
    notif_schedule: bool = typer.Option(None, help="Schedule reminders"),
):
    """Update fields in a user's profile."""
    _require_host_user(username)
    updates = {}
    if theme: updates["theme"] = theme
    if email: updates["email"] = email
    if display_name: updates["display_name"] = display_name
    notif_updates = {}
    if notif_network is not None: notif_updates["network_events"] = notif_network
    if notif_config is not None: notif_updates["config_changes"] = notif_config
    if notif_security is not None: notif_updates["security_alerts"] = notif_security
    if notif_schedule is not None: notif_updates["schedule_reminders"] = notif_schedule
    if notif_updates:
        current = profile_core.get_user_profile(username)
        merged = current.get("notifications", {})
        merged.update(notif_updates)
        updates["notifications"] = merged
    if updates:
        profile_core.update_user_profile(username, updates)
        typer.echo(f"Profile updated for {username}")
    else:
        typer.echo("No updates specified.")

@cli.command()
def themes():
    """List available themes."""
    themes = list_theme_names()
    for key, name in themes.items():
        typer.echo(f"{key}: {name}")

@cli.command()
def autogen():
    """Auto-create all missing user profiles for host users in required groups."""
    users_added = 0
    for group, level in [("lnmtadm", "admin"), ("lnmt", "operator"), ("lnmtv", "viewer")]:
        try:
            members = grp.getgrnam(group).gr_mem
            for u in members:
                if not profile_core.user_profile_exists(u):
                    profile_core.create_user_profile(u, access_level=level)
                    typer.echo(f"Created profile for {u} (from group {group})")
                    users_added += 1
        except KeyError:
            continue
    typer.echo(f"Auto-generated {users_added} user profiles.")

