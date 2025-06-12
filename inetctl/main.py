import typer

# Import the Typer "app" objects from each of our CLI modules
from inetctl.cli import access, config, dnsmasq, network, shorewall, show, tc
from inetctl.core.config_loader import find_config_file
from inetctl.web.app import app as flask_app

# This is our main Typer application
app = typer.Typer(
    help="inetctl - Your Home Network Management Tool.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

# Add all the subcommand groups
app.add_typer(config.app)
app.add_typer(show.app)
app.add_typer(dnsmasq.app)
app.add_typer(network.app)
app.add_typer(shorewall.app)
app.add_typer(tc.app)
app.add_typer(access.app)

# --- Web Portal Command ---
web_app = typer.Typer(
    name="web", help="Run the inetctl web portal.", no_args_is_help=True
)


def print_flask_routes():
    """Helper to print all registered Flask routes for debugging."""
    print("DEBUG: Registered Flask routes:")
    for rule in sorted(flask_app.url_map.iter_rules(), key=lambda r: r.rule):
        print(f"  - {rule.rule}  Methods: {','.join(rule.methods)}")


@web_app.command("serve")
def web_serve_cmd():
    """Starts the inetctl web portal."""
    from inetctl.core.config_loader import load_config  # Local import

    config = load_config()
    web_config = config.get("web_portal", {})
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8080)
    debug = web_config.get("debug", False)

    if debug:
        print_flask_routes()

    typer.echo(
        typer.style(f"Starting inetctl web portal at http://{host}:{port}", fg=typer.colors.GREEN)
    )
    if not find_config_file():
        typer.echo(
            typer.style(
                "Warning: No config file found. Web portal may have limited functionality.",
                fg=typer.colors.YELLOW,
            )
        )

    flask_app.run(host=host, port=port, debug=debug)


app.add_typer(web_app)

if __name__ == "__main__":
    app()
