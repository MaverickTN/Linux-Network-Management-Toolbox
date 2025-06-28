import argparse
from lnmt.core import self_heal

def run(args):
    if args.subcommand == "status":
        self_heal.show_status()
    elif args.subcommand == "log":
        self_heal.show_log()
    elif args.subcommand == "test":
        self_heal.test_heal(args.module)

def setup_parser(parser):
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser("status")
    subparsers.add_parser("log")
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("module")
