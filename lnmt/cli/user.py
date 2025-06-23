import typer
import getpass
import pwd
from lnmt.core.auth import require_group
from lnmt.theme import cli_color

app = typer.Typer(name="user", help="Manage users and permissions")

@app.command("current")
@require_group(["lnmtadm", "lnmt", "lnmtv"])
def show_current_user():
    """Show current user and group memberships."""
    user = getpass.getuser()
    user_info = pwd.getpwnam(user)
    print(cli_color(f"User: {user}", "primary"))
    print(cli_color(f"UID: {user_info.pw_uid}", "info"))
    print(cli_color(f"GID: {user_info.pw_gid}", "info"))
    print(cli_color(f"Home: {user_info.pw_dir}", "info"))

@app.command("check")
@require_group(["lnmtadm"])
def check_user_group(username: str):
    """Check if user belongs to one of the LNMT groups."""
    import grp
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    found = [g for g in groups if g in ["lnmtadm", "lnmt", "lnmtv"]]
    if found:
        print(cli_color(f"User '{username}' in: {found}", "success"))
    else:
        print(cli_color(f"User '{username}' is not in any LNMT group", "danger"))
