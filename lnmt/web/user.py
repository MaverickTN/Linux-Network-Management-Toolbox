# lnmt/web/user.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from lnmt.core.user_manager import (
    get_current_user_profile,
    update_user_profile,
    update_user_theme,
    validate_and_update_password,
    get_theme_list,
)
from flask_login import login_required, current_user

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user_profile(current_user.username)
    themes = get_theme_list()
    if request.method == 'POST':
        # Profile update
        if 'update_profile' in request.form:
            email = request.form.get('email')
            notify_options = request.form.getlist('notify_options')
            update_user_profile(user['username'], email=email, notify_options=notify_options)
            flash('Profile updated.', 'success')
        # Password update
        elif 'update_password' in request.form:
            old_pw = request.form.get('old_password')
            new_pw = request.form.get('new_password')
            confirm_pw = request.form.get('confirm_password')
            result, msg = validate_and_update_password(user['username'], old_pw, new_pw, confirm_pw)
            if result:
                flash('Password updated.', 'success')
            else:
                flash(msg, 'danger')
        # Theme update
        elif 'update_theme' in request.form:
            theme = request.form.get('theme')
            update_user_theme(user['username'], theme)
            session['theme'] = theme
            flash('Theme updated.', 'success')
        return redirect(url_for('user.profile'))
    return render_template(
        'user_profile.html',
        user=user,
        themes=themes,
        selected_theme=session.get('theme', user.get('theme', 'dark'))
    )
