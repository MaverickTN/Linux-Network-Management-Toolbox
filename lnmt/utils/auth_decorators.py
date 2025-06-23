import typer
from functools import wraps
import getpass
import os
from lnmt.utils.auth import (
    pam_authenticate,
    user_role,
    can_run_cli,
    can_run_admin,
    forbid_if_not_authorized
)

def require_cli_auth(role_required="operator"):
    """
    Typer decorator to require CLI authentication and correct group membership.
    If running as root, allow. Otherwise, prompt for username/password.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = os.getenv("USER") or getpass.getuser()
            if username == "root":
                # Root always allowed
                return func(*args, **kwargs)
            role = user_role(username)
            if not role:
                typer.echo("You are not in any allowed LNMT group. Access denied.")
                raise typer.Exit(code=1)
            if role_required == "admin" and role != "admin":
                typer.echo("This command requires LNMT admin privileges.")
                raise typer.Exit(code=1)
            # Optionally re-authenticate via PAM
            password = getpass.getpass(f"Password for {username}: ")
            ok, msg = pam_authenticate(username, password)
            if not ok:
                typer.echo(f"Authentication failed: {msg}")
                raise typer.Exit(code=1)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Flask middleware for web authentication and group checks
def require_web_auth(role_required="operator"):
    """
    Flask decorator for routes that require login and group membership.
    Assumes user session is managed with flask-login or similar.
    """
    from flask import session, redirect, url_for, flash, request
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            username = session.get("username")
            if not username:
                flash("Login required", "danger")
                return redirect(url_for("login", next=request.url))
            role = user_role(username)
            if not role:
                flash("Not a member of any authorized group.", "danger")
                return redirect(url_for("logout"))
            if role_required == "admin" and role != "admin":
                flash("Admin privileges required.", "danger")
                return redirect(url_for("index"))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator

# Helper for direct programmatic use (e.g., scripts)
def check_cli_access_or_exit(role_required="operator"):
    username = os.getenv("USER") or getpass.getuser()
    if username == "root":
        return True
    role = user_role(username)
    if not role:
        typer.echo("You are not in any allowed LNMT group. Access denied.")
        raise typer.Exit(code=1)
    if role_required == "admin" and role != "admin":
        typer.echo("This command requires LNMT admin privileges.")
        raise typer.Exit(code=1)
    return True
