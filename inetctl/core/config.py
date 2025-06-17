import click
from inetctl.core import config_loader
from inetctl.Job_queue_service import job_queue_service

@click.group()
def cli():
    """Network Toolbox Configuration CLI"""

@cli.command()
@click.option('--title', prompt="Site title", help="Set the site title shown on all pages")
def set_title(title):
    """Set the application site title."""
    job_id = job_queue_service.add_job("set_title", title=title)
    click.echo(f"Title change queued as job {job_id}")
    show_job_progress(job_id)

@cli.command()
def show():
    """Show current configuration."""
    config = config_loader.load_config()
    click.echo("Current configuration:")
    for k, v in config.items():
        click.echo(f"{k}: {v}")

def show_job_progress(job_id):
    import time
    from rich import print
    click.echo("Tracking job progress...")
    while True:
        status, msg = job_queue_service.get_status(job_id)
        print(f"Status: {status} | {msg}")
        if status in ("success", "failed", "notfound"):
            break
        time.sleep(1)
    steps = job_queue_service.get_job_steps(job_id)
    for step in steps:
        print(f"[{step['time']}] {step['message']}")

if __name__ == "__main__":
    cli()
