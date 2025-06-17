import typer
from inetctl.cli import scheduler, blocklist, reservation, theme

app = typer.Typer(help="Linux Network Management Toolbox CLI Menu")

app.add_typer(scheduler.app, name="schedule")
app.add_typer(blocklist.app, name="blocklist")
app.add_typer(reservation.app, name="reservation")
app.add_typer(theme.app, name="theme")

@app.command("menu")
def main_menu():
    """
    Interactive main menu for all CLI functions.
    """
    print("\n--- Linux Network Management Toolbox CLI ---")
    print("1. Schedule Host Blacklist Blocks")
    print("2. Block/Unblock Host")
    print("3. Manage DHCP Reservations")
    print("4. Theme Selection")
    print("5. Exit")
    choice = typer.prompt("Choose an option", type=int)
    if choice == 1:
        scheduler.schedule_menu()
    elif choice == 2:
        blocklist.block_menu()
    elif choice == 3:
        reservation.reservation_menu()
    elif choice == 4:
        theme.theme_menu()
    else:
        raise typer.Exit(0)

if __name__ == "__main__":
    app()
