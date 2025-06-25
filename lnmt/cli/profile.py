#!/usr/bin/env python3

import typer
from lnmt.core.auth import require_access
from lnmt.core.profile import get_user_profile, update_user_profile, get_user_role, set_user_role

app = typer.Typer()

@app.command("show")
@require_access("operator")
def show_profile(username: str):
    """Show profile information for a user."""
    profile = get_user_profile(username)
    if profile:
        typer.echo(f"User: {profile['username']}, Role: {profile['role']}, Created: {profile['created']}")
    else:
        typer.echo(f"No profile found for {username}")

@app.command("set-role")
@require_access("admin")
def change_role(username: str, role: str):
    """Set the role for a user."""
    try:
        set_user_role(username, role)
        typer.echo(f"Role for {username} updated to {role}")
    except ValueError as e:
        typer.echo(str(e))
