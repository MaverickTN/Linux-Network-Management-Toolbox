#!/usr/bin/env python3

import typer
from lnmt.core.auth import require_access
from lnmt.core.dnsmasq import add_reservation, remove_reservation, load_reservations, reload_dnsmasq

app = typer.Typer()

@app.command("list")
@require_access("operator")
def list_reservations():
    """List all configured static reservations."""
    reservations = load_reservations()
    for r in reservations:
        typer.echo(f"{r['mac']} -> {r['ip']} {r.get('hostname', '')}")

@app.command("add")
@require_access("admin")
def add(mac: str, ip: str, hostname: str = ""):
    """Add a static DHCP reservation."""
    add_reservation(mac, ip, hostname)
    reload_dnsmasq()
    typer.echo(f"Added reservation for {mac} -> {ip} ({hostname})")

@app.command("remove")
@require_access("admin")
def remove(mac: str):
    """Remove a reservation by MAC address."""
    remove_reservation(mac)
    reload_dnsmasq()
    typer.echo(f"Removed reservation for {mac}")
