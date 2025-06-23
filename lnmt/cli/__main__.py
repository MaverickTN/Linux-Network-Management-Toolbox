import typer

from lnmt.cli.user import app as user_app
from lnmt.cli.network import app as network_app
# You would add more: from lnmt.cli.dnsmasq import app as dnsmasq_app, etc.

app = typer.Typer(name="lnmt", help="Linux Network Management Toolbox (CLI)")

app.add_typer(user_app, name="user")
app.add_typer(network_app, name="network")
# Add other modules here as you modularize: app.add_typer(dnsmasq_app, name="dnsmasq")

if __name__ == "__main__":
    app()
