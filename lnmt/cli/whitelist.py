def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manage DNS whitelist")
    parser.add_argument("action", choices=["list", "add", "remove"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--description", help="Optional description")
    args = parser.parse_args()

    if args.action == "list":
        print("Listing whitelisted domains...")
    elif args.action == "add":
        print(f"Adding domain: {args.value} (desc: {args.description})")
    elif args.action == "remove":
        print(f"Removing domain: {args.value}")
