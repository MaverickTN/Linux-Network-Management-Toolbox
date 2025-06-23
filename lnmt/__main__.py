# lnmt/__main__.py

import sys
import typer
from lnmt.cli import config, schedule, blocklist, reservations
from lnmt.core.config_loader import load_config

app = typer.Typer(help="Linux Network Management Toolbox CLI")

app.add_typer(config.app, name="config")
app.add_typer(schedule.app, name="schedule")
app.add_typer(blocklist.app, name="blocklist")
app.add_typer(reservations.app, name="reservations")

@app.command()
def runserver():
    """Start the LNMT web interface."""
    from lnmt.app import create_app
    config = load_config()
    flask_app = create_app()
    flask_app.run(
        host=config['web_portal'].get('host', '0.0.0.0'),
        port=int(config['web_portal'].get('port', 8080)),
        debug=bool(config['web_portal'].get('debug', False))
    )

if __name__ == "__main__":
    app()
