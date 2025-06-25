#!/usr/bin/env python3

from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.web.utils import require_web_role
import sqlite3
from datetime import datetime

config_routes = Blueprint("config_routes", __name__)
DB_PATH = "/etc/lnmt/lnmt_stats.db"

def get_config():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lnmt_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated TEXT
        )
    """)
    cur.execute("SELECT key, value FROM lnmt_config")
    config = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return config

def set_config(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO lnmt_config (key, value, updated)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated = excluded.updated
    """, (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

@require_web_role("admin")
@config_routes.route("/config", methods=["GET"])
def config_view():
    config = get_config()
    return render_template("config.html", config=config)

@require_web_role("admin")
@config_routes.route("/config/update", methods=["POST"])
def config_update():
    for key in request.form:
        set_config(key, request.form[key])
    flash("Configuration updated", "success")
    return redirect(url_for("config_routes.config_view"))
