import typer
import getpass
from lnmt.core.user_profiles import (
    load_profile, save_profile, set_theme,
    set_notifications, set_email, list_profiles,
    update_profile
)
from lnmt.theme import list_theme_names

app = typer.Typer(
    name="profile",
    help="Manage user profile settings (theme, notifications, email, etc.)",
    no_args_is_help=True,
)

@app.command("show")
def show_profile(
    username: str = typer.Option(None, help="Username to show profile for (default: current user)")
):
    """Display current user profile."""
    username = username or getpass.getuser()
    profile = load_profile(username)
    typer.echo(f"Profile for {username}:\n")
    for k, v in profile.items():
        typer.echo(f"{k}: {v}")

@app.command("theme")
def select_theme(
    theme: str = typer.Option(None, "--theme", "-t", help="Theme to set (see: list-themes)"),
    username: str = typer.Option(None, help="Username (default: current user)"),
):
    """Set your preferred theme."""
    username = username or getpass.getuser()
    themes = list_theme_names()
    if not theme:
        typer.echo("Available themes:")
        for k, v in themes.items():
            typer.echo(f"{k}: {v}")
        theme = typer.prompt("Enter theme key", default="dark")
    if theme not in themes:
        typer.secho("Invalid theme!", fg=typer.colors.RED)
        raise typer.Exit(1)
    set_theme(username, theme)
    typer.secho(f"Theme set to {theme} ({themes[theme]})", fg=typer.colors.GREEN)

@app.command("notifications")
def set_notifications_cli(
    events: str = typer.Option(None, "--events", "-e", help="Comma-separated event types (e.g., login,config_change)"),
    username: str = typer.Option(None, help="Username (default: current user)"),
):
    """Set notification events."""
    username = username or getpass.getuser()
    if not events:
        events = typer.prompt("Enter comma-separated notification events (e.g., login,config_change,important)", default="important,login")
    event_list = [x.strip() for x in events.split(",") if x.strip()]
    set_notifications(username, event_list)
    typer.secho(f"Notification events updated: {event_list}", fg=typer.colors.GREEN)

@app.command("email")
def set_email_cli(
    email: str = typer.Option(None, help="Email address for notifications"),
    username: str = typer.Option(None, help="Username (default: current user)"),
):
    """Set notification email."""
    username = username or getpass.getuser()
    if not email:
        email = typer.prompt("Enter email address")
    set_email(username, email)
    typer.secho(f"Email updated: {email}", fg=typer.colors.GREEN)

@app.command("edit")
def edit_profile(
    username: str = typer.Option(None, help="Username (default: current user)"),
    display_name: str = typer.Option(None, "--name", "-n", help="Display name"),
    email: str = typer.Option(None, help="Email address"),
    theme: str = typer.Option(None, help="Theme key"),
    notification_events: str = typer.Option(None, help="Comma-separated event list")
):
    """Edit multiple fields at once."""
    username = username or getpass.getuser()
    update = {}
    if display_name: update["display_name"] = display_name
    if email: update["email"] = email
    if theme: update["theme"] = theme
    if notification_events:
        update["notification_events"] = [x.strip() for x in notification_events.split(",") if x.strip()]
    if not update:
        typer.echo("No changes provided.")
        raise typer.Exit()
    profile = update_profile(username, **update)
    typer.secho(f"Profile updated for {username}.", fg=typer.colors.GREEN)
    for k, v in update.items():
        typer.echo(f"{k}: {v}")

@app.command("list")
def list_all_profiles():
    """List all user profiles on the system."""
    users = list_profiles()
    typer.echo("User profiles found:")
    for user in users:
        typer.echo(user)

if __name__ == "__main__":
    app()
