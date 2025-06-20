import typer
import getpass
import os
from inetctl.auth.pam_auth import (
    authenticate_and_initialize,
    list_all_profiles
)
from inetctl.theme import cli_color, get_theme

# Import CLI modules
from inetctl.cli.config import app as config_app
from inetctl.cli.dnsmasq import app as dnsmasq_app
from inetctl.cli.schedule import app as schedule_app
from inetctl.cli.tc import app as tc_app
# ... import all CLI modules as needed

cli = typer.Typer(
    help="Linux Network Management Toolbox - Unified CLI"
)
cli.add_typer(config_app, name="config")
cli.add_typer(dnsmasq_app, name="dnsmasq")
cli.add_typer(schedule_app, name="schedule")
cli.add_typer(tc_app, name="tc")
# ... add other command groups here

def check_auth_and_profile():
    username = os.getenv("USER") or getpass.getuser()
    password = None
    if os.geteuid() != 0:
        password = getpass.getpass(prompt="Password for {}: ".format(username))
    success, msg, group = authenticate_and_initialize(username, password)
    if not success:
        typer.echo(cli_color(msg, "danger"))
        raise typer.Exit(code=1)
    # Set theme for CLI
    theme_key = "dark"
    try:
        # Attempt to fetch user's preferred theme from profile
        for profile in list_all_profiles():
            if profile[0] == username:
                theme_key = profile[2]
    except Exception:
        pass
    return theme_key, username, group

@cli.callback()
def cli_entry():
    """
    Pre-execution authentication and profile setup for LNMT CLI.
    """
    theme_key, username, group = check_auth_and_profile()
    # Display welcome banner with theme
    typer.echo(cli_color(
        f"\nWelcome {username} to the Linux Network Management Toolbox CLI ({group})", "primary", theme_key
    ))

@cli.command("profiles")
def list_profiles():
    """
    List all LNMT user profiles (admin only).
    """
    theme_key, username, group = check_auth_and_profile()
    if group != "lnmtadm":
        typer.echo(cli_color("Only lnmtadm members can view profiles.", "danger", theme_key))
        raise typer.Exit(code=1)
    users = list_all_profiles()
    if not users:
        typer.echo(cli_color("No LNMT profiles found.", "warning", theme_key))
        return
    for u in users:
        typer.echo(cli_color(
            f"User: {u[0]}, Group: {u[1]}, Theme: {u[2]}, Email: {u[3]}, Notify: {u[4]}, Created: {u[5]}",
            "info", theme_key
        ))

if __name__ == "__main__":
    cli()
