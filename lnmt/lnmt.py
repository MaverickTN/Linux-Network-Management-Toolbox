#!/usr/bin/env python3

import sys
import typer
from lnmt.core.auth import get_logged_in_user, cli_access
from lnmt.cli.main_menu import app as cli_app
from lnmt.core.job_queue_service import JobQueueService
from lnmt.core.traffic_monitor import traffic_loop
from lnmt.core.ip_tracker import ip_tracker_loop
import threading
from lnmt.core.schedule import load_schedules, remove_expired_blocks
import time

app = typer.Typer()

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, service: bool = typer.Option(False, "--service", help="Run LMNT as a background service")):
    username = get_logged_in_user()

    if service:
        if not cli_access(username):
            typer.echo("Access denied: You do not have permission to run the service.")
            raise typer.Exit(code=1)
        typer.echo("Starting LMNT Job Queue Service...")
        job_service = JobQueueService()
        job_service.start()

        # Start traffic and IP tracking in background
        threading.Thread(target=traffic_loop, daemon=True).start()
        threading.Thread(target=ip_tracker_loop, daemon=True).start()
        schedules = load_schedules()
        for mac in schedules.keys():
            remove_expired_blocks(mac)
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            typer.echo("Shutting down job queue service...")
            job_service.stop()
        return

    if ctx.invoked_subcommand:
        return  # Allow Typer to handle subcommand normally

    # No args: Launch menu only if user has access
    if not cli_access(username):
        typer.echo("Access denied: CLI menu not permitted for this user.")
        raise typer.Exit(code=1)

    cli_app()

if __name__ == "__main__":
    app()
