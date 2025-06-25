#!/usr/bin/env python3

from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.web.utils import require_web_role
import sqlite3
from datetime import datetime

reservations_routes = Blueprint("reservations_routes", __name__)
DB_PATH = "/etc/lnmt/lnmt_stats.db"

def init_reservation_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            mac TEXT PRIMARY KEY,
            hostname TEXT,
            ip TEXT,
            notes TEXT,
            updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_all_reservations():
    init_reservation_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT mac, hostname, ip, notes FROM reservations ORDER BY ip")
    rows = cur.fetchall()
    conn.close()
    return rows

def upsert_reservation(mac, hostname, ip, notes):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservations (mac, hostname, ip, notes, updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(mac) DO UPDATE SET
            hostname = excluded.hostname,
            ip = excluded.ip,
            notes = excluded.notes,
            updated = excluded.updated
    """, (mac, hostname, ip, notes, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def delete_reservation(mac):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM reservations WHERE mac = ?", (mac,))
    conn.commit()
    conn.close()

@require_web_role("operator")
@reservations_routes.route("/reservations", methods=["GET"])
def reservations_list():
    rows = get_all_reservations()
    return render_template("reservations.html", reservations=rows)

@require_web_role("admin")
@reservations_routes.route("/reservations/add", methods=["POST"])
def reservation_add():
    upsert_reservation(
        request.form.get("mac"),
        request.form.get("hostname"),
        request.form.get("ip"),
        request.form.get("notes")
    )
    flash("Reservation added/updated.", "success")
    return redirect(url_for("reservations_routes.reservations_list"))

@require_web_role("admin")
@reservations_routes.route("/reservations/delete/<mac>")
def reservation_delete(mac):
    delete_reservation(mac)
    flash("Reservation deleted.", "info")
    return redirect(url_for("reservations_routes.reservations_list"))
