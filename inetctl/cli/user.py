import typer
from inetctl.core.auth import add_user, hash_password, get_user_by_name

app = typer.Typer(
    name="user",
    help="Manage system users for web UI access.",
    no_args_is_help=True
)

@app.command("add")
def add_user_cmd(
    username: str = typer.Argument(..., help="The username to create."),
    role: str = typer.Option("operator", "--role", help="The role to assign (admin, operator, viewer).")
):
    """
    Adds a new user to the inetctl database.
    """
    if role not in ['admin', 'operator', 'viewer']:
        typer.echo(typer.style(f"Error: Role must be one of 'admin', 'operator', or 'viewer'.", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    existing_user, _ = get_user_by_name(username)
    if existing_user:
        typer.echo(typer.style(f"Error: User '{username}' already exists.", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    password = typer.prompt("Enter new user's password", hide_input=True)
    password_confirm = typer.prompt("Confirm password", hide_input=True)

    if password != password_confirm:
        typer.echo(typer.style("Error: Passwords do not match.", fg=typer.colors.RED))
        raise typer.Exit(code=1)

    password_hash = hash_password(password)
    
    if add_user(username, password_hash, role):
        typer.echo(typer.style(f"Successfully created user '{username}' with role '{role}'.", fg=typer.colors.GREEN))
    else:
        typer.echo(typer.style(f"Error: Could not create user '{username}'.", fg=typer.colors.RED))
        raise typer.Exit(code=1)