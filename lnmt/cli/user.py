# lnmt/cli/user.py

import typer
from lnmt.core.database import get_connection
from lnmt.core.user_manager import auto_create_profile, is_system_user, user_group_membership, get_user_theme_from_db

app = typer.Typer(
    name="user",
    help="User profile and access management.",
    no_args_is_help=True
)

@app.command("list")
def list_users():
    """List all user profiles in the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, theme, email FROM user_profiles")
    users = c.fetchall()
    for user in users:
        typer.echo(f"User: {user[0]}, Theme: {user[1]}, Email: {user[2]}")

@app.command("create")
def create_user(username: str, email: str = typer.Option(None, help="User email")):
    """Manually create a user profile for a system user."""
    conn = get_connection()
    if not is_system_user(username):
        typer.echo(f"User '{username}' does not exist on system.")
        raise typer.Exit(1)
    result = auto_create_profile(username, conn)
    if result:
        typer.echo(f"Created user profile for '{username}'.")
        if email:
            c = conn.cursor()
            c.execute("UPDATE user_profiles SET email=? WHERE username=?", (email, username))
            conn.commit()
    else:
        typer.echo(f"Profile for '{username}' already exists or user not in allowed group.")

@app.command("theme")
def set_theme(username: str, theme: str):
    """Set the CLI and web theme for a user."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE user_profiles SET theme=? WHERE username=?", (theme, username))
    conn.commit()
    typer.echo(f"Theme for '{username}' set to {theme}.")

if __name__ == "__main__":
    app()
