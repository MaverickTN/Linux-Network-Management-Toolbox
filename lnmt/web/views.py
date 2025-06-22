from flask import Blueprint, render_template, session
from inetctl.web.auth import require_auth
from inetctl.profile import get_profile

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
@require_auth
def home():
    username = session.get("user")
    profile = get_profile(username)
    return render_template(
        "home.html",
        username=username,
        profile=profile,
        theme_key=profile.get("theme", session.get("theme", "dark"))
    )

@home_bp.route('/profile')
@require_auth
def profile_page():
    username = session.get("user")
    profile = get_profile(username)
    return render_template(
        "profile.html",
        username=username,
        profile=profile
    )
