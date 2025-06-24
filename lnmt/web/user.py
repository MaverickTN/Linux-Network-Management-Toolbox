# lnmt/web/user.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from lnmt.core.auth import authenticate_user
from lnmt.core.database import get_connection
from lnmt.core.user_manager import get_user_theme_from_db

bp = Blueprint('user', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate_user(username, password):
            session['username'] = username
            session['theme'] = get_user_theme_from_db(username)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Invalid credentials or unauthorized group membership.', 'danger')
    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('theme', None)
    flash('Logged out.', 'info')
    return redirect(url_for('user.login'))

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('user.login'))
    username = session['username']
    conn = get_connection()
    c = conn.cursor()
    if request.method == 'POST':
        theme = request.form['theme']
        email = request.form['email']
        c.execute("UPDATE user_profiles SET theme=?, email=? WHERE username=?", (theme, email, username))
        conn.commit()
        session['theme'] = theme
        flash('Profile updated.', 'success')
    c.execute("SELECT theme, email FROM user_profiles WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    profile = {'theme': row[0] if row else 'dark', 'email': row[1] if row else ''}
    return render_template('profile.html', profile=profile)
