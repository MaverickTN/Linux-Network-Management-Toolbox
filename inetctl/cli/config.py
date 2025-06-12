import json
from pathlib import Path
from typing import Dict, Any

import typer

# Import the core logic functions from our new modules
from inetctl.core.config_loader import (
    LOADED_CONFIG_PATH,
    find_config_file,
    load_config,
    save_config,
)

# Define a new Typer application for the 'config' subcommand
app = typer.Typer(
    name="config", help="Manage and view inetctl configuration.", no_args_is_help=True
)


@app.command("init")
def config_init(
    force: bool = typer.Option(
        False, "--force", help="Force overwrite of existing configuration file."
    )
):
    """Creates an initial 'server_config.json' file interactively."""
    typer.echo(typer.style("--- Initial Configuration Setup ---", bold=True))

    existing_config = find_config_file()
    save_path = None

    if existing_config and not force:
        typer.echo(
            typer.style(
                f"Warning: Configuration file already exists at {existing_config}",
                fg=typer.colors.YELLOW,
            )
        )
        if not typer.confirm("Do you want to overwrite it?"):
            raise typer.Abort()
        save_path = existing_config

    if not save_path:
        typer.echo("Choose where to save the new configuration file:")
        typer.echo("1: In the current directory (./server_config.json)")
        typer.echo(f"2: In the user config directory (~/.config/inetctl/server_config.json)")
        choice = typer.prompt("Enter choice (1 or 2)", type=int, default=1)
        if choice == 1:
            save_path = Path("./server_config.json")
        elif choice == 2:
            save_path = Path.home() / ".config" / "inetctl" / "server_config.json"
        else:
            typer.echo(typer.style("Invalid choice.", fg=typer.colors.RED))
            raise typer.Exit(1)

    typer.echo(typer.style(f"\nGathering essential settings for {save_path}", bold=True))

    default_config = {
        "global_settings": {
            "wan_interface": typer.prompt(
                "Enter your primary WAN interface name", default="eth0"
            ),
            "primary_host_lan_interface_base": typer.prompt(
                "Enter your primary LAN interface name (base for VLANs)", default="eth1"
            ),
            "dnsmasq_config_dir": typer.prompt(
                "Enter path to Dnsmasq config directory", default="/etc/dnsmasq.d"
            ),
            "dnsmasq_leases_file": typer.prompt(
                "Enter path to Dnsmasq leases file",
                default="/var/lib/misc/dnsmasq.leases",
            ),
            "netplan_config_dir": typer.prompt(
                "Enter path to Netplan config directory", default="/etc/netplan"
            ),
            "shorewall_snat_file_path": typer.prompt(
                "Enter path to Shorewall 'snat' file", default="/etc/shorewall/snat"
            ),
            "default_lan_upload_speed": "100mbit",
            "default_lan_download_speed": "1000mbit",
        },
        "web_portal": {"host": "0.0.0.0", "port": 8080, "debug": False},
        "networks": [],
        "hosts_dhcp_reservations": [],
        "remote_hosts": [],
        "wireguard_hub_peers": [],
        "traffic_control_policies": [
            {
                "id": "bulk-downloads",
                "description": "For devices that can use lots of bandwidth but are not priority.",
                "rate_down": "500mbit",
                "ceil_down": "800mbit",
                "rate_up": "10mbit",
                "ceil_up": "20mbit",
            },
            {
                "id": "priority-gaming",
                "description": "Low latency and high priority for gaming consoles.",
                "rate_down": "800mbit",
                "ceil_down": "1000mbit",
                "rate_up": "50mbit",
                "ceil_up": "80mbit",
                "priority": 1,
            },
            {
                "id": "iot-limited",
                "description": "Very limited bandwidth for IoT devices.",
                "rate_down": "5mbit",
                "ceil_down": "10mbit",
                "rate_up": "1mbit",
                "ceil_up": "2mbit",
                "priority": 7,
            },
        ],
        "access_control_schedules": [],
    }

    if save_config(default_config, path_override=save_path):
        typer.echo(
            typer.style(
                "\nInitial configuration created successfully.",
                fg=typer.colors.GREEN,
                bold=True,
            )
        )
        typer.echo("You can now add networks and hosts to this file.")


@app.command("validate")
def config_validate():
    """Validates the inetctl configuration file (existence, JSON validity, key sections)."""
    try:
        config = load_config(force_reload=True)

        required_top_level = [
            "global_settings",
            "networks",
            "hosts_dhcp_reservations",
            "traffic_control_policies",
        ]
        missing_sections = [s for s in required_top_level if s not in config]
        if missing_sections:
            typer.echo(
                typer.style(
                    f"Warning: Config missing essential sections: {', '.join(missing_sections)}",
                    fg=typer.colors.YELLOW,
                )
            )

        gs = config.get("global_settings", {})
        essential_global_keys = [
            "dnsmasq_config_dir",
            "primary_host_lan_interface_base",
            "wan_interface",
            "netplan_config_dir",
            "dnsmasq_leases_file",
        ]
        missing_global_keys = [k for k in essential_global_keys if k not in gs]
        if missing_global_keys:
            for k in missing_global_keys:
                typer.echo(
                    typer.style(
                        f"Warning: Global setting '{k}' not found.",
                        fg=typer.colors.YELLOW,
                    )
                )

        typer.echo(
            typer.style(
                f"Configuration file at {LOADED_CONFIG_PATH} loaded and is valid JSON.",
                fg=typer.colors.GREEN,
            )
        )
        if not missing_sections and not missing_global_keys:
            typer.echo(
                typer.style("Basic structural validation passed.", fg=typer.colors.GREEN)
            )

    except typer.Exit:
        if LOADED_CONFIG_PATH:
            typer.echo(
                typer.style(
                    f"Validation failed for config at {LOADED_CONFIG_PATH}.",
                    fg=typer.colors.RED,
                )
            )
        else:
            typer.echo(
                typer.style(
                    "Validation failed: No configuration file could be loaded.",
                    fg=typer.colors.RED,
                )
            )


@app.command("show")
def config_show(
    raw: bool = typer.Option(False, "--raw", help="Display the raw JSON configuration.")
):
    """Displays the loaded inetctl configuration (summary or raw JSON)."""
    config = load_config()
    if raw:
        typer.echo(json.dumps(config, indent=2))
    else:
        typer.echo(typer.style("Loaded Configuration Summary:", bold=True))
        if LOADED_CONFIG_PATH:
            typer.echo(f"  Config file path: {LOADED_CONFIG_PATH}")
        else:
            typer.echo(
                typer.style(
                    "  Warning: Config path not determined.", fg=typer.colors.YELLOW
                )
            )

        sections_to_summarize = {
            "Global Settings": config.get("global_settings"),
            "Web Portal": config.get("web_portal"),
            "Remote Hosts": config.get("remote_hosts"),
            "Networks (VLANs)": config.get("networks"),
            "DHCP Reservations": config.get("hosts_dhcp_reservations"),
            "WireGuard Hub Peers": config.get("wireguard_hub_peers"),
            "Traffic Control Policies": config.get("traffic_control_policies"),
            "Access Control Schedules": config.get("access_control_schedules"),
        }

        for name, content in sections_to_summarize.items():
            if content is None:
                typer.echo(
                    typer.style(
                        f"\n{name}: (Section not defined)", fg=typer.colors.YELLOW
                    )
                )
                continue

            count_info = f" ({len(content)} entries)" if isinstance(content, list) else ""
            typer.echo(typer.style(f"\n{name}:{count_info}", fg=typer.colors.BLUE))

            if not content:
                typer.echo("    (No entries)")
            elif isinstance(content, dict):
                for key, value in content.items():
                    typer.echo(f"  - {key}: {value}")
