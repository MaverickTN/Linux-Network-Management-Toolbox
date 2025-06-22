# inetctl/web/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user, login_required
import pam
import pwd
from inetctl.core.user_profile import UserProfile, get_or_create_user_profile, get_system_group_membership
from inetctl.core.theme_manager import get_theme_names

auth_bp = Blueprint('auth', __name__)

def pam_authenticate(username, password):
    p = pam.pam()
    return p.authenticate(username, password)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        # Only allow logins for real host users
        try:
            pwd.getpwnam(username)
        except KeyError:
            flash("User does not exist on this system.", "danger")
            return render_template("login.html", themes=get_theme_names())

        # Authenticate with PAM
        if pam_authenticate(username, password):
            # Auto-create user profile if needed
            profile, created = get_or_create_user_profile(username)
            # Check group membership for access
            groups = get_system_group_membership(username)
            allowed = any(g in ["lnmtadm", "lnmt", "lnmtv"] for g in groups)
            if not allowed:
                flash("User is not in any permitted network management group (lnmtadm/lnmt/lnmtv).", "danger")
                return render_template("login.html", themes=get_theme_names())
            # Flask-login: log user in (custom integration assumed)
            login_user(profile)
            flash(f"Welcome, {username}! You are now logged in.", "success")
            return redirect(url_for('home.dashboard'))
        else:
            flash("Authentication failed.", "danger")
            return render_template("login.html", themes=get_theme_names())
    else:
        return render_template("login.html", themes=get_theme_names())

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
