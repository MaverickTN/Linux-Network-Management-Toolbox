import argparse
from lnmt.core import backup_restore

def run(args):
    if args.subcommand == "run":
        backup_restore.run_backup(args.type, args.target)
    elif args.subcommand == "list":
        backup_restore.list_backups()
    elif args.subcommand == "restore":
        backup_restore.restore_backup(args.backup_id)
    elif args.subcommand == "export":
        backup_restore.export_backup(args.backup_id)
    elif args.subcommand == "policy":
        if args.action == "set":
            backup_restore.set_policy(args.value)
        else:
            backup_restore.get_policy()

def setup_parser(parser):
    subparsers = parser.add_subparsers(dest="subcommand")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--type", required=True)
    run_parser.add_argument("--target", required=False)

    subparsers.add_parser("list")

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("backup_id", type=int)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("backup_id", type=int)

    policy_parser = subparsers.add_parser("policy")
    policy_parser.add_argument("action", choices=["set", "get"])
    policy_parser.add_argument("value", nargs="?")
