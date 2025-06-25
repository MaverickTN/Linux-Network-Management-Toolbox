#!/usr/bin/env python3

import argparse
import getpass
from lnmt.core.auth_roles import get_user_roles, user_has_permission, init_auth_schema

def cli_check(args):
    init_auth_schema()
    user = args.user or getpass.getuser()
    roles = get_user_roles(user)
    print(f"User: {user}")
    print("Roles:")
    for r in roles:
        print(f"  - {r}")
    if args.perm:
        has = user_has_permission(user, args.perm)
        print(f"Has permission '{args.perm}': {'YES' if has else 'NO'}")

def main():
    parser = argparse.ArgumentParser(description="LNMT Role & Permission CLI")
    parser.add_argument("-u", "--user", help="Username to check (default: current user)")
    parser.add_argument("-p", "--perm", help="Check for specific permission")
    args = parser.parse_args()
    cli_check(args)

if __name__ == "__main__":
    main()
