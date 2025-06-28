import argparse
from lnmt.core import scheduler

def run(args):
    if args.subcommand == "list":
        scheduler.list_jobs()
    elif args.subcommand == "run":
        scheduler.run_job(args.job_id)
    elif args.subcommand == "log":
        scheduler.show_job_log(args.job_id)
    elif args.subcommand == "add":
        scheduler.add_job(args.name, args.action, args.schedule, args.params)
    elif args.subcommand == "edit":
        scheduler.edit_job(args.job_id, args.enable)

def setup_parser(parser):
    subparsers = parser.add_subparsers(dest="subcommand")

    subparsers.add_parser("list")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("job_id", type=int)

    log_parser = subparsers.add_parser("log")
    log_parser.add_argument("job_id", type=int)

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--action", required=True)
    add_parser.add_argument("--schedule", required=True)
    add_parser.add_argument("--params", required=False, default="{}")

    edit_parser = subparsers.add_parser("edit")
    edit_parser.add_argument("job_id", type=int)
    edit_parser.add_argument("--enable", action="store_true")
