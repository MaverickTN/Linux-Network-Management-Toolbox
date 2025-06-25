#!/usr/bin/env python3

import os
from lnmt.core import netplan

def show_files():
    print("\nNetplan Configuration Files:")
    files = netplan.list_netplan_files()
    for i, file in enumerate(files):
        print(f"{i+1}. {file}")
    return files

def edit_file():
    files = show_files()
    choice = input("Select a file number to view/edit: ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(files):
        print("[!] Invalid selection.")
        return
    file = files[int(choice)-1]
    config = netplan.read_netplan_config().get(file)
    if not config:
        print("[!] Unable to read configuration.")
        return

    print("\n--- Current Netplan YAML ---")
    from pprint import pprint
    pprint(config)
    print("-----------------------------\n")

    confirm = input("Edit this file using default editor? (y/N): ").strip().lower()
    if confirm == "y":
        os.system(f"$EDITOR /etc/netplan/{file}")
        print("[*] You may want to validate or apply changes.")

def validate_and_apply():
    confirm = input("Validate and apply Netplan changes? (y/N): ").strip().lower()
    if confirm == "y":
        netplan.validate_netplan()

        confirm2 = input("Proceed with permanent apply? (y/N): ").strip().lower()
        if confirm2 == "y":
            netplan.apply_netplan()

def netplan_menu():
    while True:
        print("\n=== Netplan CLI Menu ===")
        print("1. List netplan YAML files")
        print("2. View/Edit a netplan file")
        print("3. Validate and Apply netplan")
        print("4. Exit")
        choice = input("Select an option: ").strip()
        if choice == "1":
            show_files()
        elif choice == "2":
            edit_file()
        elif choice == "3":
            validate_and_apply()
        elif choice == "4":
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    netplan_menu()
