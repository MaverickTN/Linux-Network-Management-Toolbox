import typer
from inetctl.core.auth import require_group
from inetctl.theme import cli_color
from inetctl.core.netplan import get_all_netplan_interfaces, reload_netplan_config, parse_netplan_config

app = typer.Typer(
    name="network",
    help="Network interface management (view, reload, VLAN, etc.).",
    no_args_is_help=True
)

@app.command("list")
@require_group(["lnmtadm", "lnmt", "lnmtv"])
def list_interfaces():
    interfaces = get_all_netplan_interfaces()
    typer.echo(cli_color("Network Interfaces:", "primary"))
    for iface in interfaces:
        typer.echo(f"- {iface}")

@app.command("show")
@require_group(["lnmtadm", "lnmt", "lnmtv"])
def show_config():
    config = parse_netplan_config()
    typer.echo(cli_color("Netplan YAML:", "primary"))
    typer.echo(config)

@app.command("reload")
@require_group(["lnmtadm"])
def reload_netplan():
    success = reload_netplan_config()
    if success:
        typer.echo(cli_color("Netplan reloaded.", "success"))
    else:
        typer.echo(cli_color("Failed to reload netplan.", "danger"))

@app.command("menu")
@require_group(["lnmtadm", "lnmt"])
def interactive_menu():
    while True:
        typer.echo(cli_color("\n--- Network Menu ---", "primary"))
        typer.echo("1. List Interfaces\n2. Show Netplan Config\n3. Reload Netplan\n4. Exit")
        choice = typer.prompt("Select an option")
        if choice == "1":
            list_interfaces()
        elif choice == "2":
            show_config()
        elif choice == "3":
            reload_netplan()
        elif choice == "4":
            break
        else:
            typer.echo(cli_color("Invalid choice.", "warning"))
