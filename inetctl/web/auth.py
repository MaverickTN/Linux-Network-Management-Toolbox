import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import db, UserProfile
import pam  # python-pam library

auth_bp = Blueprint('auth', __name__)

REQUIRED_GROUPS = {
    "lnmtadm": "admin",
    "lnmt": "operator",
    "lnmtv": "view"
}

def get_user_role_from_groups(username):
    """Determine the user's highest privilege role based on host group membership."""
    import grp
    user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
    # Check by priority
    for group, role in [("lnmtadm", "admin"), ("lnmt", "operator"), ("lnmtv", "view")]:
        if group in user_groups:
            return role
    return None

def system_user_exists(username):
    """Check if the username exists on the system."""
    import pwd
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # PAM authentication
        p = pam.pam()
        if p.authenticate(username, password):
            if not system_user_exists(username):
                flash("Invalid system user.", "danger")
                return render_template("login.html")
            role = get_user_role_from_groups(username)
            if not role:
                flash("User not a member of any LNMT group (lnmtadm, lnmt, lnmtv).", "danger")
                return render_template("login.html")
            # Auto-create user profile if needed
            user = UserProfile.query.filter_by(username=username).first()
            if not user:
                user = UserProfile(username=username, role=role)
                db.session.add(user)
                db.session.commit()
            session['username'] = username
            session['role'] = role
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for('main.index'))
        else:
            flash("Authentication failed.", "danger")
    return render_template("login.html")

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('auth.login'))
