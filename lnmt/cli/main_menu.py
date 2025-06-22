import typer
import sys
import os
from inetctl.core.auth import (
    get_logged_in_user, check_access, require_access
)
from inetctl.core.theme import get_theme, cli_color, list_theme_names
from inetctl.core.user_profile import load_user_profile

app = typer.Typer(help="Linux Network Management Toolbox CLI")

# CLI modules (to be imported if/when modularized)
import inetctl.cli.config as config_cli
import inetctl.cli.schedule as schedule_cli
import inetctl.cli.reservations as reservations_cli
import inetctl.cli.blocklist as blocklist_cli
import inetctl.cli.netplan as netplan_cli

# Register subcommands
app.add_typer(config_cli.app, name="config")
app.add_typer(schedule_cli.app, name="schedule")
app.add_typer(reservations_cli.app, name="reservations")
app.add_typer(blocklist_cli.app, name="blocklist")
app.add_typer(netplan_cli.app, name="netplan")

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def show_welcome():
    username = get_logged_in_user()
    try:
        profile = load_user_profile(username)
        theme = get_theme(profile.get("theme", "dark"))
        access = profile.get("access_level", "view")
    except Exception:
        theme = get_theme("dark")
        access = "unknown"
    typer.echo(cli_color(f"\nWelcome to Linux Network Management Toolbox (CLI)", "primary", theme_key=theme["name"].lower()))
    typer.echo(cli_color(f"Logged in as: {username} (Access: {access})", "info", theme_key=theme["name"].lower()))
    typer.echo(cli_color("Type --help or select an option from the menu.\n", "accent", theme_key=theme["name"].lower()))

def show_menu():
    menu = [
        "1. Config  - Manage server configuration",
        "2. Schedule - Set/modify schedule blocks",
        "3. Reservations - DHCP/static reservations",
        "4. Blocklist - Network access control",
        "5. Netplan - Interface & VLAN management",
        "6. Theme - Select your CLI theme",
        "7. User Profile - Show/Edit your profile",
        "0. Exit"
    ]
    typer.echo("\n".join(menu))

def pick_theme():
    theme_names = list_theme_names()
    typer.echo("\nAvailable Themes:")
    for key, name in theme_names.items():
        typer.echo(f"  {key}: {name}")
    selected = typer.prompt("Theme key (or Enter for dark)", default="dark")
    if selected not in theme_names:
        typer.echo(cli_color("Invalid theme key. Keeping current.", "warning"))
        return
    username = get_logged_in_user()
    try:
        profile = load_user_profile(username)
        profile["theme"] = selected
        from inetctl.core.user_profile import save_user_profile
        save_user_profile(username, profile)
        typer.echo(cli_color(f"Theme set to {theme_names[selected]}.", "success", theme_key=selected))
    except Exception as e:
        typer.echo(cli_color(f"Failed to save theme: {e}", "danger"))

def show_profile():
    username = get_logged_in_user()
    try:
        profile = load_user_profile(username)
        typer.echo(cli_color(f"User: {username}", "primary", profile.get("theme", "dark")))
        for k, v in profile.items():
            typer.echo(f"  {k}: {v}")
    except Exception as e:
        typer.echo(cli_color(f"Could not load profile: {e}", "danger"))

@app.command()
def menu():
    """Interactive menu for all CLI features."""
    clear_screen()
    show_welcome()
    while True:
        show_menu()
        try:
            opt = int(typer.prompt("Enter choice"))
        except Exception:
            opt = -1
        clear_screen()
        show_welcome()
        if opt == 1:
            config_cli.app()
        elif opt == 2:
            schedule_cli.app()
        elif opt == 3:
            reservations_cli.app()
        elif opt == 4:
            blocklist_cli.app()
        elif opt == 5:
            netplan_cli.app()
        elif opt == 6:
            pick_theme()
        elif opt == 7:
            show_profile()
        elif opt == 0:
            typer.echo(cli_color("Goodbye!", "primary"))
            sys.exit(0)
        else:
            typer.echo(cli_color("Invalid option.", "danger"))

if __name__ == "__main__":
    app()
