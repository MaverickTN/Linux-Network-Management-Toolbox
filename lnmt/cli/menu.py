import typer
from typing import Optional
import sys

from lnmt.cli import config_cli, schedule_cli, reservation_cli, blocklist_cli, user_cli

app = typer.Typer(
    name="lnmt",
    help="Linux Network Management Toolbox CLI",
    no_args_is_help=True
)

# Add subcommands for each module
app.add_typer(config_cli.app, name="config")
app.add_typer(schedule_cli.app, name="schedule")
app.add_typer(reservation_cli.app, name="reservation")
app.add_typer(blocklist_cli.app, name="blocklist")
app.add_typer(user_cli.app, name="user")

def main_menu():
    print("\n=== Linux Network Management Toolbox CLI ===")
    print("Select a section:")
    print("1. Config management")
    print("2. Host schedules")
    print("3. Reservations")
    print("4. Blocklist")
    print("5. User accounts")
    print("0. Exit")
    choice = input("\nEnter option: ").strip()
    return choice

def run_menu():
    while True:
        choice = main_menu()
        if choice == "1":
            config_cli.app()
        elif choice == "2":
            schedule_cli.app()
        elif choice == "3":
            reservation_cli.app()
        elif choice == "4":
            blocklist_cli.app()
        elif choice == "5":
            user_cli.app()
        elif choice == "0":
            print("Exiting. Goodbye.")
            sys.exit(0)
        else:
            print("Invalid option. Try again.")

@app.callback()
def main(
    menu: Optional[bool] = typer.Option(
        None,
        "--menu",
        help="Force interactive menu (default if no args)."
    )
):
    # If no args or --menu, show menu; otherwise, parse args normally.
    if (len(sys.argv) == 1 and menu is None) or (menu is True):
        run_menu()

if __name__ == "__main__":
    app()
