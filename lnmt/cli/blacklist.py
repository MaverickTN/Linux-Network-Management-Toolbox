def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manage blacklist rules")
    parser.add_argument("action", choices=["list", "add", "delete", "toggle", "snooze", "hits"])
    parser.add_argument("params", nargs="*")
    args = parser.parse_args()

    print(f"{args.action.capitalize()} blacklist rule(s): {' '.join(args.params)}")
