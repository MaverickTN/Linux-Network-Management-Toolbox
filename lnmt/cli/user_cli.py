import typer
import getpass
import grp
import pwd
from inetctl.core.config_loader import (
    load_config, save_config, validate_config, backup_config
)
from inetctl.core.user import (
    create_profile_for_host_user, is_host_user, valid_group_for_cli,
    list_profiles, set_profile_theme, set_profile_notifications
)

app = typer.Typer(
    name="user",
    help="User and profile management for the Linux Network Management Toolbox."
)

@app.command("list")
def list_users():
    """List all user profiles managed by LNMT."""
    profiles = list_profiles()
    if not profiles:
        typer.secho("No user profiles found.", fg=typer.colors.YELLOW)
        return
    for idx, user in enumerate(profiles, 1):
        typer.echo(f"{idx}. {user['username']} ({user['group']}) | Theme: {user['theme']} | Email: {user.get('email', 'n/a')}")

@app.command("create")
def create_user(
    username: str = typer.Argument(..., help="Username"),
    group: str = typer.Option("lnmt", help="User group (lnmtadm, lnmt, lnmtv)"),
    email: str = typer.Option(None, help="User email"),
    theme: str = typer.Option("dark", help="Default theme")
):
    """Create a new user profile (LNMT only, not system user)."""
    if is_host_user(username):
        typer.secho("Error: Cannot create LNMT user matching a system user for security.", fg=typer.colors.RED)
        raise typer.Exit(1)
    config = load_config()
    users = config.setdefault("user_profiles", [])
    if any(u["username"] == username for u in users):
        typer.secho("User already exists.", fg=typer.colors.RED)
        raise typer.Exit(1)
    users.append({
        "username": username,
        "group": group,
        "theme": theme,
        "email": email,
        "notifications": {"all": True},
    })
    backup_config()
    save_config(config)
    typer.secho(f"User '{username}' created.", fg=typer.colors.GREEN)
    validate_config()

@app.command("remove")
def remove_user(
    username: str = typer.Argument(..., help="Username to remove")
):
    """Remove a user profile."""
    config = load_config()
    users = config.setdefault("user_profiles", [])
    for i, u in enumerate(users):
        if u["username"] == username:
            del users[i]
            backup_config()
            save_config(config)
            typer.secho(f"Removed user {username}.", fg=typer.colors.GREEN)
            validate_config()
            return
    typer.secho("User not found.", fg=typer.colors.RED)

@app.command("set-theme")
def set_theme(
    username: str = typer.Argument(..., help="Username"),
    theme: str = typer.Argument(..., help="Theme name")
):
    """Set a user's CLI/web theme."""
    result = set_profile_theme(username, theme)
    if result:
        typer.secho(f"Theme updated for {username} → {theme}", fg=typer.colors.GREEN)
    else:
        typer.secho("Theme or user not found.", fg=typer.colors.RED)

@app.command("set-email")
def set_email(
    username: str = typer.Argument(..., help="Username"),
    email: str = typer.Argument(..., help="Email")
):
    """Set user's email."""
    config = load_config()
    users = config.setdefault("user_profiles", [])
    for u in users:
        if u["username"] == username:
            u["email"] = email
            backup_config()
            save_config(config)
            typer.secho(f"Email set for {username}.", fg=typer.colors.GREEN)
            validate_config()
            return
    typer.secho("User not found.", fg=typer.colors.RED)

@app.command("set-notifications")
def set_notifications(
    username: str = typer.Argument(..., help="Username"),
    all: bool = typer.Option(True, "--all/--no-all", help="Enable all notifications"),
    events: str = typer.Option("", help="Comma-separated event types")
):
    """Set user's notification preferences."""
    events_list = [e.strip() for e in events.split(",") if e.strip()]
    set_profile_notifications(username, all, events_list)
    typer.secho(f"Notifications updated for {username}.", fg=typer.colors.GREEN)

@app.command("auto-create-host")
def auto_create_host_profiles():
    """
    Scan for host users in allowed groups, auto-create LNMT profiles if not present.
    """
    for g in ["lnmtadm", "lnmt", "lnmtv"]:
        try:
            members = grp.getgrnam(g).gr_mem
            for user in members:
                created = create_profile_for_host_user(user, g)
                if created:
                    typer.secho(f"Profile auto-created for {user} ({g})", fg=typer.colors.GREEN)
        except KeyError:
            continue

@app.command("show")
def show_profile(
    username: str = typer.Argument(..., help="Username")
):
    """Show a user's profile."""
    profiles = list_profiles()
    user = next((u for u in profiles if u["username"] == username), None)
    if not user:
        typer.secho("User not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.echo(typer.style(str(user), fg=typer.colors.CYAN))

@app.command("validate")
def validate():
    """Validate all user profiles for consistency and security."""
    validate_config()
    typer.secho("All profiles validated.", fg=typer.colors.GREEN)
