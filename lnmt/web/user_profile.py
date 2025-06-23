# lnmt/web/user_profile.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from lnmt.theme import THEMES, get_theme, list_theme_names
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

user_profile_bp = Blueprint('user_profile', __name__, template_folder='templates')

def get_db():
    import os
    db_path = os.environ.get("lnmt_DB_PATH", "/etc/lnmt/lnmt.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@user_profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        # Handle profile update
        email = request.form.get("email")
        theme = request.form.get("theme")
        notify = request.form.getlist("notifications")
        theme = theme if theme in THEMES else "dark"
        cur.execute("UPDATE users SET email=?, theme=?, notifications=? WHERE username=?",
                    (email, theme, ",".join(notify), current_user.username))
        db.commit()
        flash("Profile updated.", "success")
        session["theme"] = theme
        return redirect(url_for("user_profile.profile"))

    # Get user info
    cur.execute("SELECT * FROM users WHERE username=?", (current_user.username,))
    user = cur.fetchone()
    db.close()
    notifications = user["notifications"].split(",") if user and user["notifications"] else []
    return render_template(
        "profile.html",
        theme=user["theme"] if user else "dark",
        theme_names=list_theme_names(),
        email=user["email"] if user else "",
        notifications=notifications
    )

@user_profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT password FROM users WHERE username=?", (current_user.username,))
    user = cur.fetchone()
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if not user or not check_password_hash(user["password"], old_password):
        flash("Old password is incorrect.", "danger")
        return redirect(url_for("user_profile.profile"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("user_profile.profile"))
    if len(new_password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("user_profile.profile"))
    new_hash = generate_password_hash(new_password)
    cur.execute("UPDATE users SET password=? WHERE username=?", (new_hash, current_user.username))
    db.commit()
    db.close()
    flash("Password changed successfully.", "success")
    return redirect(url_for("user_profile.profile"))

@user_profile_bp.route("/profile/theme", methods=["POST"])
@login_required
def change_theme():
    theme = request.form.get("theme")
    if theme not in THEMES:
        theme = "dark"
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE users SET theme=? WHERE username=?", (theme, current_user.username))
    db.commit()
    db.close()
    session["theme"] = theme
    return jsonify(success=True, theme=theme)

