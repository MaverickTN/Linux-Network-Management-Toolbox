import typer
from typing import List

from inetctl.core.utils import (
    check_root_privileges,
    run_command,
    get_shorewall_dynamic_blocked, # CORRECTED import location and name
)

app = typer.Typer(
    name="access",
    help="Manually manage device access via the dynamic block list.",
    no_args_is_help=True
)

@app.command(name="block")
def block_ip(
    ips: List[str] = typer.Argument(..., help="One or more IP addresses to block."),
):
    """Adds an IP address to the dynamic 'blocked' zone in Shorewall."""
    check_root_privileges("block IPs")
    for ip in ips:
        typer.echo(f"Blocking {ip}...")
        run_command(["sudo", "shorewall", "add", "blocked", ip])
    typer.echo(typer.style("Done.", fg=typer.colors.GREEN))

@app.command(name="unblock")
def unblock_ip(
    ips: List[str] = typer.Argument(..., help="One or more IP addresses to unblock."),
):
    """Removes an IP address from the dynamic 'blocked' zone in Shorewall."""
    check_root_privileges("unblock IPs")
    for ip in ips:
        typer.echo(f"Unblocking {ip}...")
        run_command(["sudo", "shorewall", "delete", "blocked", ip])
    typer.echo(typer.style("Done.", fg=typer.colors.GREEN))

@app.command(name="list")
def list_blocked():
    """Lists dynamically blocked IPs in Shorewall."""
    check_root_privileges("list blocked IPs")
    typer.echo("Currently blocked dynamic IPs in Shorewall:")
    
    # CORRECTED function call
    currently_blocked = get_shorewall_dynamic_blocked() 
    
    if currently_blocked:
        for ip in currently_blocked:
            typer.echo(f" - {ip}")
    else:
        typer.echo("No hosts are dynamically blocked.")