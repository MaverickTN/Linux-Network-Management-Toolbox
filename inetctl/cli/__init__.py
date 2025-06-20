from .config import cli as config_cli
from .profile import cli as profile_cli
from .schedule import cli as schedule_cli
# ... Add more as you modularize

__all__ = [
    "config_cli",
    "profile_cli",
    "schedule_cli"
]
