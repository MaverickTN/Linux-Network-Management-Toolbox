# lnmt/core/menu_cli.py

import typer
from lnmt.core.user_manager import is_authorized, get_lnmt_role

def print_banner():
    print("==== Linux Network Management Toolbox (LNMT) ====")

def menu_for_role(role):
    if role == "admin":
        return [
            ("1", "Show configuration", "config_show"),
            ("2", "Initialize config", "config_init"),
            ("3", "Manage users", "user_manage"),
            ("4", "Schedule tasks", "schedule_tasks"),
            ("5", "Show logs", "show_logs"),
            ("q", "Quit", None)
        ]
    elif role == "operator":
        return [
            ("1", "Show configuration", "config_show"),
            ("2", "Schedule tasks", "schedule_tasks"),
            ("q", "Quit", None)
        ]
    else:
        return [
            ("1", "Show configuration", "config_show"),
            ("q", "Quit", None)
        ]

def main_menu(username):
    role = get_lnmt_role(username)
    if role is None:
        print("Access denied: You are not a member of any permitted LNMT group.")
        return
    while True:
        print_banner()
        print(f"User: {username} ({role})")
        options = menu_for_role(role)
        for key, desc, _ in options:
            print(f"{key}. {desc}")
        choice = input("Select an option: ").strip()
        for key, _, action in options:
            if choice == key:
                if action == "config_show":
                    from lnmt.cli.config import show_config_path
                    show_config_path()
                elif action == "config_init":
                    from lnmt.cli.config import init_config
                    init_config(force=True)
                elif action == "user_manage":
                    print("User management not yet implemented.")
                elif action == "schedule_tasks":
                    print("Task scheduling menu not yet implemented.")
                elif action == "show_logs":
                    print("Log viewing not yet implemented.")
                elif action is None:
                    print("Quitting.")
                    return
                break
        else:
            print("Invalid selection. Try again.")

if __name__ == "__main__":
    import getpass
    user = getpass.getuser()
    main_menu(user)
