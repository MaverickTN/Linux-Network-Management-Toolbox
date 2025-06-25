import shutil
from lnmt.core.admin_eventlog import log_admin_event

def safe_write_config(filepath, content, actor="system", validate_func=None, rollback=True):
    backup_path = filepath + ".bak"
    try:
        # Backup current config
        shutil.copy(filepath, backup_path)

        # Write new config
        with open(filepath, "w") as f:
            f.write(content)

        # Validate
        if validate_func and not validate_func(filepath):
            raise ValueError("Validation failed")

        log_admin_event("config_update", actor=actor, target=filepath, success=True)
        return True
    except Exception as e:
        if rollback:
            shutil.copy(backup_path, filepath)
        log_admin_event("config_update", actor=actor, target=filepath, success=False, details=str(e))
        return False
