#!/usr/bin/env python3

from flask import redirect, url_for, flash
from functools import wraps
from lnmt.web.auth import get_logged_in_role

def require_web_role(required):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            role = get_logged_in_role()
            if role == "admin":
                return func(*args, **kwargs)
            if role == required:
                return func(*args, **kwargs)
            flash("Access denied: insufficient permissions", "danger")
            return redirect(url_for("auth_routes.login"))
        return wrapper
    return decorator
