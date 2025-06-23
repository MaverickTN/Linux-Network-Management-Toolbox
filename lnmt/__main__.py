import typer
import os
import sys
from getpass import getuser
from lnmt.cli.config import app as config_app
from lnmt.cli.user_cli import app as user_app
from lnmt.cli.schedule_cli import app as schedule_app
from lnmt.cli.reservation_cli import app as reservation_app
from lnmt.cli.blocklist_cli import app as blocklist_app
from lnmt.theme import get_theme, THEMES
from lnmt.core.user import valid_group_for_cli

cli = typer.Typer(
    help="Linux Network Management Toolbox (LNMT): Unified CLI interface.",
    no_args_is_help=True
)

cli.add_typer(config_app, name="config")
cli.add_typer(user_app, name="user")
cli.add_typer(schedule_app, name="schedule")
cli.add_typer(reservation_app, name="reservation")
cli.add_typer(blocklist_app, name="blocklist")

@cli.callback()
def check_user_and_theme():
    """Ensure only authorized users can access, and set CLI theme."""
    user = getuser()
    if not valid_group_for_cli(user):
        typer.secho("Access denied: user must be in lnmtadm, lnmt, or lnmtv group.", fg=typer.colors.RED)
        raise typer.Exit(1)
    # Set CLI colors based on user profile (if set)
    try:
        from lnmt.core.config_loader import load_config
        config = load_config()
        user_profiles = config.get("user_profiles", [])
        user_profile = next((u for u in user_profiles if u["username"] == user), None)
        theme_key = user_profile.get("theme", "dark") if user_profile else "dark"
        if theme_key in THEMES:
            os.environ["LNMT_CLI_THEME"] = theme_key
    except Exception:
        os.environ["LNMT_CLI_THEME"] = "dark"

@cli.command("menu")
def interactive_menu():
    """
    Interactive, menu-driven LNMT CLI (safe for non-root users in correct group).
    """
    import questionary
    from rich.console import Console

    user = getuser()
    theme = get_theme(os.environ.get("LNMT_CLI_THEME", "dark"))
    console = Console()
    while True:
        console.print(f"[bold {theme['primary']}]Linux Network Management Toolbox CLI[/bold {theme['primary']}]")
        option = questionary.select(
            "Choose an action:",
            choices=[
                "Config", "Users", "Schedule", "Reservations", "Blocklist", "Exit"
            ]).ask()
        if option == "Config":
            os.system(f"{sys.executable} {sys.argv[0]} config")
        elif option == "Users":
            os.system(f"{sys.executable} {sys.argv[0]} user")
        elif option == "Schedule":
            os.system(f"{sys.executable} {sys.argv[0]} schedule")
        elif option == "Reservations":
            os.system(f"{sys.executable} {sys.argv[0]} reservation")
        elif option == "Blocklist":
            os.system(f"{sys.executable} {sys.argv[0]} blocklist")
        else:
            break
    console.print(f"[{theme['success']}]Goodbye, {user}![/]")

if __name__ == "__main__":
    cli()

