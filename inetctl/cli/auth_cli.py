# inetctl/cli/auth_cli.py

import typer
import getpass
import grp
import pwd
import os
from inetctl.core.user_profile import get_or_create_user_profile
from inetctl.theme import THEMES, cli_color

app = typer.Typer(
    name="auth",
    help="User authentication and profile management."
)

LNMT_GROUPS = {
    "lnmtadm": "Admin",
    "lnmt": "Operator",
    "lnmtv": "View Only"
}

@app.command("whoami")
def whoami():
    user = getpass.getuser()
    groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem or g.gr_gid == pwd.getpwnam(user).pw_gid]
    typer.echo(cli_color(f"Current user: {user}", "primary"))
    typer.echo(f"Group(s): {', '.join(groups)}")
    for g in LNMT_GROUPS:
        if g in groups:
            typer.echo(cli_color(f"LNMT Role: {LNMT_GROUPS[g]}", "success"))
            break
    else:
        typer.echo(cli_color("LNMT Role: None - CLI access may be restricted.", "danger"))

@app.command("theme")
def show_theme():
    user = getpass.getuser()
    profile, _ = get_or_create_user_profile(user)
    theme_key = profile.get("theme", "dark")
    theme = THEMES.get(theme_key, THEMES["dark"])
    typer.echo(f"Theme: {theme['name']}")
    for k in ["primary", "background", "foreground", "accent"]:
        v = theme[k]
        typer.echo(cli_color(f"{k.title()}: {v}", "primary", theme_key))

@app.command("groups")
def show_lnmt_groups():
    typer.echo("LNMT Host Groups:")
    for k, v in LNMT_GROUPS.items():
        typer.echo(f"  {k} : {v}")

if __name__ == "__main__":
    app()
