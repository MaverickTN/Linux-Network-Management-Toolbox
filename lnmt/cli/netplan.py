def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manage Netplan configurations")
    parser.add_argument("action", choices=["list", "add", "edit", "delete", "stage"])
    parser.add_argument("name", nargs="?")
    parser.add_argument("file", nargs="?")
    args = parser.parse_args()

    print(f"{args.action.capitalize()} Netplan config: {args.name or ''}")
