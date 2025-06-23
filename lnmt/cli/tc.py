import typer
from lnmt.job_queue_service import JobQueueService
from lnmt.theme import cli_color
from lnmt.core.tc import (
    list_qos_profiles,
    apply_qos_profile,
    remove_qos_profile,
    list_host_qos
)

app = typer.Typer(help="Manage traffic control / QoS profiles.")
job_queue = JobQueueService()

@app.command("profiles")
def show_profiles():
    """List available QoS profiles."""
    profiles = list_qos_profiles()
    typer.echo(cli_color("Available QoS Profiles:", "primary"))
    for name, prof in profiles.items():
        typer.echo(f"  {name}: {prof['description']} (DL: {prof['guaranteed_mbit']}-{prof['limit_mbit']} Mbps)")

@app.command("apply")
def apply_qos(mac: str, profile: str):
    """Apply a QoS profile to a host."""
    job_id = job_queue.enqueue("apply_qos_profile", {"mac": mac, "profile": profile})
    typer.echo(cli_color(f"QoS profile '{profile}' queued for {mac} (job id: {job_id})", "success"))

@app.command("remove")
def remove_qos(mac: str):
    """Remove QoS limits from a host."""
    job_id = job_queue.enqueue("remove_qos_profile", {"mac": mac})
    typer.echo(cli_color(f"Remove QoS queued for {mac} (job id: {job_id})", "warning"))

@app.command("host")
def host_qos(mac: str):
    """Show current QoS profile for a host."""
    qos = list_host_qos(mac)
    if qos:
        typer.echo(cli_color(f"{mac}: Profile {qos['profile']} (DL: {qos['download']} UL: {qos['upload']})", "info"))
    else:
        typer.echo(cli_color(f"No QoS set for {mac}", "warning"))
