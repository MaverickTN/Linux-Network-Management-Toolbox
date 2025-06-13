import typer
from typing import List
from inetctl.core.utils import (
    check_root_privileges,
    run_command,
    get_shorewall_blacklisted_ips,
)

# This Typer application defines the 'inetctl access' command group.
# The help text is a single, clean string.
app = typer.Typer(
    name="access",
    help="Manually manage device access via the Shorewall blacklist.",
    no_args_is_help=True
)

@app.command(name="block")
def block_ip(
    ips: List[str] = typer.Argument(..., help="One or more IP addresses to block."),
):
    """
    Adds one or more IP addresses to the dynamic blacklist.
    This function uses the 'shorewall reject' command.
    """
    check_root_privileges("block IPs")
    for ip in ips:
        typer.echo(f"Blacklisting (rejecting) {ip}...")
        run_command(["sudo", "shorewall", "reject", ip])
    typer.echo(typer.style("Done.", fg=typer.colors.GREEN))

@app.command(name="unblock")
def unblock_ip(
    ips: List[str] = typer.Argument(..., help="One or more IP addresses to unblock."),
):
    """
    Removes one or more IP addresses from the dynamic blacklist.
    This function uses the 'shorewall allow' command.
    """
    check_root_privileges("unblock IPs")
    for ip in ips:
        typer.echo(f"Un-blacklisting (allowing) {ip}...")
        run_command(["sudo", "shorewall", "allow", ip])
    typer.echo(typer.style("Done.", fg=typer.colors.GREEN))

@app.command(name="list")
def list_blocked():
    """
    Lists all IPs currently in the dynamic blacklist.
    This function uses the 'shorewall show blacklists' command.
    """
    check_root_privileges("list blacklisted IPs")
    typer.echo("Currently blacklisted IPs in Shorewall:")
    
    # This calls the correct helper function in utils.py
    currently_blocked = get_shorewall_blacklisted_ips() 
    
    if currently_blocked:
        for ip in currently_blocked:
            typer.echo(f" - {ip}")
    else:
        typer.echo("The blacklist is empty.")