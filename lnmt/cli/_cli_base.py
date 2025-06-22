import os
import typer
import getpass
from inetctl.utils.auth import allowed_cli_access, get_cli_role
from inetctl.theme import get_theme, cli_color

class CLIContext:
    user: str = None
    role: str = None
    theme_key: str = "dark"

cli_context = CLIContext()

def check_cli_access():
    user = getpass.getuser()
    cli_context.user = user
    cli_context.role = get_cli_role(user)
    if not allowed_cli_access(user):
        typer.echo(cli_color(
            f"Error: User '{user}' is not in a permitted group for CLI access.", "danger"
        ))
        raise typer.Exit(1)
    # Optionally: load preferred theme from user profile/db
    # For now, use group to select theme for demonstration:
    if cli_context.role == "admin":
        cli_context.theme_key = "dark"
    elif cli_context.role == "operator":
        cli_context.theme_key = "oceanic"
    elif cli_context.role == "viewer":
        cli_context.theme_key = "solarized"
    else:
        cli_context.theme_key = "dark"

def themed_echo(text, style="primary"):
    typer.echo(cli_color(text, style, cli_context.theme_key))
