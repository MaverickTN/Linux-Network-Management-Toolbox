import typer
import getpass
from pathlib import Path

from inetctl.core.user import (
    load_profile,
    save_profile,
    get_access_level,
    update_profile,
    get_all_profiles,
    auto_provision_profile,
    REQUIRED_GROUPS,
    check_user_allowed
)
from inetctl.theme import THEMES, list_theme_names

cli = typer.Typer(
    name="user",
    help="User profile, theme, and notification settings management"
)

@cli.command("whoami")
def whoami():
    """
    Shows your current user profile and access level.
    """
    username = getpass.getuser()
    if not check_user_allowed(username):
        typer.secho("You are not allowed to use LNMT CLI.", fg=typer.colors.RED)
        raise typer.Exit(1)
    prof = load_profile(username) or auto_provision_profile(username)
    typer.secho(f"Username: {prof['username']}", fg=typer.colors.CYAN)
    typer.echo(f"Access Level: {prof['access_level']}")
    typer.echo(f"Theme: {prof.get('theme', 'dark')}")
    typer.echo(f"Email: {prof.get('email','')}")
    typer.echo("Notification prefs:")
    for k, v in (prof.get("notify", {}) or {}).items():
        typer.echo(f"  {k}: {'on' if v else 'off'}")
    typer.echo(f"Contact: {', '.join(prof.get('contact_methods', []))}")

@cli.command("set-theme")
def set_theme(theme: str = typer.Argument(..., help="Theme key (see user list-themes)")):
    """
    Sets your theme for CLI and web.
    """
    username = getpass.getuser()
    if not check_user_allowed(username):
        typer.secho("Not allowed.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if theme not in THEMES:
        typer.secho("Invalid theme.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    update_profile(username, {"theme": theme})
    typer.secho(f"Theme set to {theme}.", fg=typer.colors.GREEN)

@cli.command("list-themes")
def list_themes():
    """
    List all available UI/CLI themes.
    """
    for k, v in list_theme_names().items():
        typer.echo(f"{k}: {v}")

@cli.command("set-notify")
def set_notify(
    on_login: bool = typer.Option(None, help="Notify on login"),
    on_schedule: bool = typer.Option(None, help="Notify on schedule event"),
    on_job_event: bool = typer.Option(None, help="Notify on job event"),
):
    """
    Update your notification preferences.
    """
    username = getpass.getuser()
    if not check_user_allowed(username):
        typer.secho("Not allowed.", fg=typer.colors.RED)
        raise typer.Exit(1)
    prof = load_profile(username) or auto_provision_profile(username)
    notify = prof.get("notify", {}) or {}
    if on_login is not None:
        notify["on_login"] = on_login
    if on_schedule is not None:
        notify["on_schedule"] = on_schedule
    if on_job_event is not None:
        notify["on_job_event"] = on_job_event
    update_profile(username, {"notify": notify})
    typer.secho("Notification preferences updated.", fg=typer.colors.GREEN)

@cli.command("set-contact")
def set_contact(
    email: str = typer.Option("", help="Email address"),
    contact_methods: str = typer.Option("", help="Contact methods, comma separated")
):
    """
    Update your contact information.
    """
    username = getpass.getuser()
    if not check_user_allowed(username):
        typer.secho("Not allowed.", fg=typer.colors.RED)
        raise typer.Exit(1)
    updates = {}
    if email:
        updates["email"] = email
    if contact_methods:
        updates["contact_methods"] = [m.strip() for m in contact_methods.split(",") if m.strip()]
    update_profile(username, updates)
    typer.secho("Contact info updated.", fg=typer.colors.GREEN)

@cli.command("list-users")
def list_users():
    """
    Admins only: List all user profiles.
    """
    username = getpass.getuser()
    prof = load_profile(username) or auto_provision_profile(username)
    if prof.get("access_level") != "admin":
        typer.secho("Admins only.", fg=typer.colors.RED)
        raise typer.Exit(1)
    for p in get_all_profiles():
        typer.echo(f"{p['username']} ({p['access_level']}), email: {p.get('email','')} theme: {p.get('theme','dark')}")
