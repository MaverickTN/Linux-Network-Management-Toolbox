from functools import wraps
from flask import request, session
from lnmt.core.admin_eventlog import log_admin_event

def require_role(required_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            user = session.get("username", "anonymous")
            role = session.get("role")
            ip = request.remote_addr
            if role in required_roles:
                return fn(*args, **kwargs)
            else:
                log_admin_event(
                    action="unauthorized_access",
                    actor=user,
                    target=request.path,
                    success=False,
                    details=f"Role '{role}' from {ip} attempted access"
                )
                return "Access denied", 403
        return decorated_view
    return wrapper
