import argparse
from lnmt.core.pihole_api import PiHoleAPI
from lnmt.core.auth import check_role, current_user_groups
from lnmt.config.loader import get_config

def main():
    check_role("dns_manage")
    parser = argparse.ArgumentParser(description="Manage Pi-hole DNS records")
    parser.add_argument("--list", action="store_true", help="List all DNS records")
    parser.add_argument("--add", nargs=2, metavar=("NAME", "IP"), help="Add or update DNS record")
    parser.add_argument("--group", help="Optional group for DNS record (with --add)")
    parser.add_argument("--delete", metavar="ID", help="Delete DNS record by ID")
    parser.add_argument("--export", metavar="FILE", help="Export all DNS records to JSON")
    parser.add_argument("--import", dest="import_file", metavar="FILE", help="Import DNS records from JSON")
    args = parser.parse_args()

    cfg = get_config(section="dns")
    api = PiHoleAPI(
        cfg["pihole_api_url"],
        cfg["pihole_api_key"],
        test_mode=cfg.getboolean("test_mode", fallback=False),
        retries=cfg.getint("retries", fallback=3),
        retry_delay=cfg.getint("retry_delay", fallback=2)
    )

    try:
        if args.list:
            records = api.list_records()
            for rec in records:
                print(f"{rec['id']}: {rec['name']} → {rec['ip']} (Group: {rec.get('group', '-')})")
        elif args.add:
            name, ip = args.add
            group = args.group or "default"
            result = api.add_or_update_record(name, ip, group)
            print("Added/Updated:", result)
        elif args.delete:
            success = api.delete_record(args.delete)
            print("Deleted." if success else "Failed to delete.")
        elif args.export:
            api.export_records(args.export)
            print(f"Exported to {args.export}")
        elif args.import_file:
            api.import_records(args.import_file)
            print(f"Imported from {args.import_file}")
    except Exception as e:
        print(str(e))
