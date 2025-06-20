import typer
from inetctl.job_queue_service import JobQueueService
from inetctl.theme import cli_color
from inetctl.core.dnsmasq import (
    list_leases,
    reload_dnsmasq,
    add_static_lease,
    remove_static_lease
)

app = typer.Typer(help="Manage DNSMasq leases and settings.")
job_queue = JobQueueService()

@app.command("leases")
def show_leases():
    """Display all current DHCP leases."""
    leases = list_leases()
    if not leases:
        typer.echo(cli_color("No leases found.", "warning"))
    for lease in leases:
        status = "STATIC" if lease.get("static") else "DYNAMIC"
        typer.echo(cli_color(
            f"{lease['mac']:17} {lease['ip']:15} {lease['hostname'] or '(unknown)':20} {status}",
            "primary" if status == "STATIC" else "info"
        ))

@app.command("add-static")
def add_static(mac: str, ip: str, hostname: str = typer.Option(None, help="Optional hostname")):
    """Add a static DHCP lease."""
    job_id = job_queue.enqueue("add_static_lease", {"mac": mac, "ip": ip, "hostname": hostname})
    typer.echo(cli_color(f"Static lease queued for {mac} → {ip} ({hostname}) (job id: {job_id})", "success"))

@app.command("remove-static")
def remove_static(mac: str):
    """Remove a static DHCP lease."""
    job_id = job_queue.enqueue("remove_static_lease", {"mac": mac})
    typer.echo(cli_color(f"Remove static lease queued for {mac} (job id: {job_id})", "warning"))

@app.command("reload")
def reload_dns():
    """Reload the DNSMasq service."""
    job_id = job_queue.enqueue("reload_dnsmasq", {})
    typer.echo(cli_color(f"Reload DNSMasq job queued (job id: {job_id})", "info"))
