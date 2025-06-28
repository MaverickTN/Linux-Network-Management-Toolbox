def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manage LNMT settings")
    parser.add_argument("action", choices=["get", "set"])
    parser.add_argument("key")
    parser.add_argument("value", nargs="?")
    args = parser.parse_args()

    if args.action == "get":
        print(f"Getting setting for: {args.key}")
    else:
        print(f"Setting {args.key} to {args.value}")
