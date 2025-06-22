import typer
from inetctl.core.profile import (
    get_user_profile,
    update_user_profile,
    list_all_profiles,
    auto_create_profile,
    get_user_role,
)
from inetctl.theme import cli_color
import getpass
import os

app = typer.Typer(name="profile", help="Manage your LNMT user profile.")

@app.command("show")
def show(username: str = typer.Option(None, help="User to show profile for (default: self)")):
    if not username:
        username = getpass.getuser()
    auto_create_profile(username)
    profile = get_user_profile(username)
    if not profile:
        print(cli_color("No profile found or access denied.", "danger"))
        raise typer.Exit(1)
    print(cli_color(f"Profile for {username}:", "primary"))
    for k, v in profile.items():
        print(cli_color(f"{k}: {v}", "info"))

@app.command("set-theme")
def set_theme(theme: str = typer.Argument(..., help="Theme key to set for your profile")):
    username = getpass.getuser()
    auto_create_profile(username)
    if update_user_profile(username, {"theme": theme}):
        print(cli_color(f"Theme updated to {theme}", "success", theme))
    else:
        print(cli_color("Failed to update theme.", "danger", theme))

@app.command("set-email")
def set_email(email: str = typer.Argument(..., help="Set your notification email")):
    username = getpass.getuser()
    auto_create_profile(username)
    if update_user_profile(username, {"email": email}):
        print(cli_color(f"Email updated to {email}", "success"))
    else:
        print(cli_color("Failed to update email.", "danger"))

@app.command("list")
def list_profiles():
    """List all profiles (admin only)."""
    username = getpass.getuser()
    role = get_user_role(username)
    if role != "admin":
        print(cli_color("Admin access required.", "danger"))
        raise typer.Exit(1)
    profiles = list_all_profiles()
    for uname, pdata in profiles.items():
        print(cli_color(f"User: {uname}", "primary"))
        for k, v in pdata.items():
            print(f"  {k}: {v}")

