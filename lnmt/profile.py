from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from .models import db, UserProfile
from .themes import THEMES

profile_bp = Blueprint("profile", __name__)

@profile_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if "username" not in session:
        flash("You must be logged in to access your profile.", "danger")
        return redirect(url_for("auth.login"))

    user = UserProfile.query.filter_by(username=session["username"]).first()
    if not user:
        flash("User profile not found.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # Update user settings
        user.theme = request.form.get("theme", user.theme)
        user.email = request.form.get("email", user.email)
        user.notify_events = request.form.getlist("notify_events")
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.profile"))

    # For password changes, show a warning; handled via system tools/PAM
    return render_template(
        "profile.html",
        user=user,
        all_themes=THEMES,
        event_options=[
            ("job_complete", "Job Complete"),
            ("config_changed", "Config Changed"),
            ("schedule_triggered", "Schedule Triggered"),
            ("blocklist_update", "Blocklist Update"),
            # Add more as needed
        ],
    )
