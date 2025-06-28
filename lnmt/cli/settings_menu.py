from lnmt.core.settings import get_setting, set_setting

def display_detection_settings():
    keys = ['ping_window', 'min_bytes_in', 'min_bytes_out']
    print("Detection Settings:")
    for key in keys:
        print(f"{key}: {get_setting(key)}")

def update_detection_setting():
    key = input("Setting key to update: ")
    value = input("New value: ")
    set_setting(key, value)
    print("Updated.")

def main():
    while True:
        print("\n1. View Detection Settings")
        print("2. Update a Setting")
        print("0. Exit")
        choice = input("Choice: ")
        if choice == "1":
            display_detection_settings()
        elif choice == "2":
            update_detection_setting()
        elif choice == "0":
            break
