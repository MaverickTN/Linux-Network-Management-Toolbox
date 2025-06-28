import argparse
from lnmt.core import proactive_reporting

def run(args):
    if args.subcommand == "digest":
        if args.now:
            proactive_reporting.send_digest()
        elif args.list:
            proactive_reporting.list_digests()

def setup_parser(parser):
    subparsers = parser.add_subparsers(dest="subcommand")

    digest_parser = subparsers.add_parser("digest")
    digest_parser.add_argument("--now", action="store_true")
    digest_parser.add_argument("--list", action="store_true")
