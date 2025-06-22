import typer
from inetctl.core.config_loader import load_config, save_config, validate_config, backup_config

app = typer.Typer(
    name="blocklist",
    help="Manage network blocklists (hosts/ranges denied network access)."
)

def find_blocklist(config):
    return config.setdefault("blocklist", [])

@app.command("list")
def list_blocked():
    """List all blocklisted hosts/ranges."""
    config = load_config()
    blocklist = find_blocklist(config)
    if not blocklist:
        typer.secho("No blocklisted entries.", fg=typer.colors.YELLOW)
        return
    for idx, entry in enumerate(blocklist, 1):
        typer.echo(f"{idx}. {entry['type'].capitalize()}: {entry['value']}")

@app.command("add")
def add_block(
    value: str = typer.Argument(..., help="IP, MAC, or CIDR range to block."),
    block_type: str = typer.Option("ip", "--type", "-t", help="Type: ip, mac, or cidr.", show_default=True)
):
    """Add a host or range to the blocklist."""
    config = load_config()
    blocklist = find_blocklist(config)
    for entry in blocklist:
        if entry["type"] == block_type and entry["value"] == value:
            typer.secho("Already blocklisted.", fg=typer.colors.RED)
            raise typer.Exit(1)
    blocklist.append({"type": block_type, "value": value})
    backup_config()
    save_config(config)
    typer.secho(f"Blocklisted {block_type}: {value}", fg=typer.colors.GREEN)
    validate_config()

@app.command("remove")
def remove_block(index: int = typer.Argument(..., help="Blocklist entry number (see list)")):
    """Remove a blocklist entry by number."""
    config = load_config()
    blocklist = find_blocklist(config)
    idx = index - 1
    if idx < 0 or idx >= len(blocklist):
        typer.secho("Invalid blocklist entry index.", fg=typer.colors.RED)
        raise typer.Exit(1)
    entry = blocklist.pop(idx)
    backup_config()
    save_config(config)
    typer.secho(f"Removed {entry['type']}: {entry['value']} from blocklist.", fg=typer.colors.GREEN)
    validate_config()

@app.command("edit")
def edit_block(
    index: int = typer.Argument(..., help="Blocklist entry number (see list)"),
    value: str = typer.Option(None, "--value", "-v", help="New value (IP, MAC, or CIDR)"),
    block_type: str = typer.Option(None, "--type", "-t", help="Type: ip, mac, or cidr")
):
    """Edit a blocklist entry."""
    config = load_config()
    blocklist = find_blocklist(config)
    idx = index - 1
    if idx < 0 or idx >= len(blocklist):
        typer.secho("Invalid blocklist entry index.", fg=typer.colors.RED)
        raise typer.Exit(1)
    entry = blocklist[idx]
    new_type = block_type if block_type else entry["type"]
    new_value = value if value else entry["value"]
    # Check for duplicates
    for i, e in enumerate(blocklist):
        if i != idx and e["type"] == new_type and e["value"] == new_value:
            typer.secho("Duplicate blocklist entry.", fg=typer.colors.RED)
            raise typer.Exit(1)
    old = entry.copy()
    entry["type"] = new_type
    entry["value"] = new_value
    backup_config()
    save_config(config)
    typer.secho(f"Blocklist entry updated: {old} → {entry}", fg=typer.colors.GREEN)
    validate_config()

@app.command("interactive")
def interactive_block():
    """Interactively add a new blocklist entry."""
    value = typer.prompt("IP, MAC, or CIDR to block")
    block_type = typer.prompt("Type (ip, mac, cidr)", default="ip")
    add_block(value, block_type)
