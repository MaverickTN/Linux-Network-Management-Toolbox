#!/usr/bin/env python3

from flask import session
from lnmt.core.profile import get_user_role

def get_logged_in_user():
    return session.get("username")

def get_logged_in_role():
    user = get_logged_in_user()
    if user:
        return get_user_role(user)
    return "guest"
