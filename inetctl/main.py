import typer

# ADD 'user' to the import list
from inetctl.cli import access, config, dnsmasq, network, shorewall, show, tc, schedule, user
from inetctl.core.config_loader import find_config_file, load_config
from inetctl.web.app import app as flask_app

app = typer.Typer(
    help="inetctl - Your Home Network Management Tool.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

app.add_typer(config.app)
app.add_typer(show.app)
app.add_typer(dnsmasq.app)
app.add_typer(network.app)
app.add_typer(shorewall.app)
app.add_typer(tc.app)
app.add_typer(access.app)
app.add_typer(schedule.app)
app.add_typer(user.app)  # <-- ADD THIS LINE

web_app = typer.Typer(name="web", help="Run the inetctl web portal.", no_args_is_help=True)

@web_app.command("serve")
def web_serve_cmd():
    """Starts the inetctl web portal with optional TLS."""
    config = load_config()
    web_config = config.get("web_portal", {})
    security_config = config.get("security", {}) # Get security settings
    host = web_config.get("host", "0.0.0.0")
    port = web_config.get("port", 8080)
    debug = web_config.get("debug", False)

    # --- TLS (HTTPS) IMPLEMENTATION ---
    ssl_context = None
    cert_path = security_config.get("tls_cert_path")
    key_path = security_config.get("tls_key_path")
    
    if cert_path and key_path:
        try:
            # This configures Flask to use HTTPS
            ssl_context = (cert_path, key_path)
            typer.echo(typer.style("TLS enabled. Server will start with HTTPS.", fg=typer.colors.GREEN))
        except FileNotFoundError:
            typer.echo(typer.style("Warning: TLS cert/key file not found. Starting with HTTP.", fg=typer.colors.YELLOW))
    
    protocol = "https" if ssl_context else "http"
    typer.echo(f"Starting inetctl web portal at {protocol}://{host}:{port}")

    if not find_config_file():
        typer.echo(typer.style("Warning: No config file found.", fg=typer.colors.YELLOW))

    # Pass the ssl_context to the run command
    flask_app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)

app.add_typer(web_app)