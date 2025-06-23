import typer
import json
from typing import Optional

from lnmt.core.hostdb import (
    list_hosts,
    get_host,
    add_host_reservation,
    delete_host,
    update_host,
    list_blocked_hosts,
    block_host,
    unblock_host,
    validate_host_db,
    backup_host_db,
    restore_host_db,
)

app = typer.Typer(
    name="host",
    help="Manage host reservations, blocklist, and QoS.",
    no_args_is_help=True
)

@app.command("list")
def list_cmd(
    blocked: bool = typer.Option(False, "--blocked", help="Show only blocked hosts"),
    reserved: bool = typer.Option(False, "--reserved", help="Show only DHCP reservations")
):
    """
    List all hosts (or filtered by reservation/block status).
    """
    if blocked:
        hosts = list_blocked_hosts()
        typer.echo("Blocked hosts:")
    elif reserved:
        hosts = [h for h in list_hosts() if h.get("reservation")]
        typer.echo("Hosts with DHCP reservation:")
    else:
        hosts = list_hosts()
        typer.echo("All hosts:")
    typer.echo(json.dumps(hosts, indent=2))

@app.command("get")
def get_cmd(mac: str = typer.Argument(..., help="Host MAC address")):
    """
    Get host info by MAC address.
    """
    host = get_host(mac)
    if host:
        typer.echo(json.dumps(host, indent=2))
    else:
        typer.echo(f"Host '{mac}' not found.")

@app.command("add")
def add_cmd(
    mac: str = typer.Argument(..., help="MAC address"),
    ip: str = typer.Option(..., prompt=True, help="Reserved IP address"),
    description: Optional[str] = typer.Option("", help="Description/hostname"),
    qos_profile: Optional[str] = typer.Option("normal", help="QoS profile"),
):
    """
    Add a DHCP reservation for a host.
    """
    ok, msg = add_host_reservation(mac, ip, description, qos_profile)
    if ok:
        typer.echo(f"Reservation added: {mac} -> {ip}")
    else:
        typer.echo(f"Failed: {msg}")

@app.command("delete")
def delete_cmd(mac: str = typer.Argument(..., help="MAC address")):
    """
    Delete host entry.
    """
    ok, msg = delete_host(mac)
    if ok:
        typer.echo(f"Host {mac} deleted.")
    else:
        typer.echo(f"Delete failed: {msg}")

@app.command("update")
def update_cmd(
    mac: str = typer.Argument(..., help="MAC address"),
    ip: Optional[str] = typer.Option(None, help="New IP"),
    description: Optional[str] = typer.Option(None, help="Description"),
    qos_profile: Optional[str] = typer.Option(None, help="QoS profile")
):
    """
    Update host reservation/QoS/description.
    """
    fields = {}
    if ip: fields["ip"] = ip
    if description: fields["description"] = description
    if qos_profile: fields["qos_profile"] = qos_profile
    ok, msg = update_host(mac, fields)
    if ok:
        typer.echo("Host updated.")
    else:
        typer.echo(f"Update failed: {msg}")

@app.command("block")
def block_cmd(mac: str = typer.Argument(..., help="MAC address")):
    """
    Blocklist (disable internet) for host.
    """
    ok, msg = block_host(mac)
    if ok:
        typer.echo(f"Host {mac} blocked.")
    else:
        typer.echo(f"Block failed: {msg}")

@app.command("unblock")
def unblock_cmd(mac: str = typer.Argument(..., help="MAC address")):
    """
    Remove host from blocklist.
    """
    ok, msg = unblock_host(mac)
    if ok:
        typer.echo(f"Host {mac} unblocked.")
    else:
        typer.echo(f"Unblock failed: {msg}")

@app.command("validate")
def validate_cmd():
    """
    Validate host database for corruption/overlap.
    """
    ok, msg = validate_host_db()
    if ok:
        typer.echo("Host database valid.")
    else:
        typer.echo(f"Validation error: {msg}")

@app.command("backup")
def backup_cmd():
    """
    Backup host database.
    """
    path = backup_host_db()
    typer.echo(f"Backup written to {path}")

@app.command("restore")
def restore_cmd(path: str = typer.Argument(..., help="Backup file to restore")):
    """
    Restore host database from backup.
    """
    ok, msg = restore_host_db(path)
    if ok:
        typer.echo("Restore complete.")
    else:
        typer.echo(f"Restore failed: {msg}")

if __name__ == "__main__":
    app()
