import typer
from lnmt.job_queue_service import JobQueueService
from lnmt.theme import cli_color
from lnmt.core import access as access_core

app = typer.Typer(help="Manage access rules for hosts (blocklist, allowlist).")
job_queue = JobQueueService()

@app.command("block")
def block_host(mac: str):
    """Block a host from accessing the network (add to Shorewall blacklist)."""
    job_id = job_queue.enqueue("block_host", {"mac": mac})
    typer.echo(cli_color(f"Host {mac} block requested (job id: {job_id})", "warning"))

@app.command("allow")
def allow_host(mac: str):
    """Allow a host by removing from the blacklist."""
    job_id = job_queue.enqueue("allow_host", {"mac": mac})
    typer.echo(cli_color(f"Host {mac} unblock requested (job id: {job_id})", "success"))

@app.command("status")
def show_access_status():
    """Show current block/allow status of all hosts."""
    results = access_core.list_access_status()
    for entry in results:
        color = "danger" if entry['blocked'] else "success"
        typer.echo(cli_color(f"{entry['mac']:17} {entry['ip']:15} {'BLOCKED' if entry['blocked'] else 'ALLOWED'}", color))
