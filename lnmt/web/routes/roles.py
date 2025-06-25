#!/usr/bin/env python3

from flask import Blueprint, render_template, request, redirect, url_for, flash
from lnmt.core.auth_roles import init_auth_schema
import sqlite3

DB_PATH = "/etc/lnmt/lnmt_stats.db"

roles_bp = Blueprint("roles_bp", __name__)

@roles_bp.route("/admin/roles")
def list_roles():
    init_auth_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM roles ORDER BY name")
    roles = cur.fetchall()

    cur.execute("SELECT id, name FROM permissions ORDER BY name")
    permissions = cur.fetchall()

    cur.execute("""
        SELECT roles.name, permissions.name
        FROM role_permissions
        JOIN roles ON roles.id = role_permissions.role_id
        JOIN permissions ON permissions.id = role_permissions.permission_id
    """)
    links = cur.fetchall()

    cur.execute("""
        SELECT group_mappings.sys_group, roles.name
        FROM group_mappings
        JOIN roles ON group_mappings.role_id = roles.id
    """)
    mappings = cur.fetchall()

    conn.close()
    return render_template("admin_roles.html", roles=roles, permissions=permissions, links=links, mappings=mappings)

@roles_bp.route("/admin/roles/add", methods=["POST"])
def add_role():
    name = request.form["name"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    flash(f"Role '{name}' added.", "success")
    return redirect(url_for("roles_bp.list_roles"))

@roles_bp.route("/admin/permissions/add", methods=["POST"])
def add_permission():
    name = request.form["name"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    flash(f"Permission '{name}' added.", "success")
    return redirect(url_for("roles_bp.list_roles"))

@roles_bp.route("/admin/link", methods=["POST"])
def link_permission():
    role_id = request.form["role_id"]
    perm_id = request.form["perm_id"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)", (role_id, perm_id))
    conn.commit()
    conn.close()
    flash("Linked permission to role.", "info")
    return redirect(url_for("roles_bp.list_roles"))

@roles_bp.route("/admin/map", methods=["POST"])
def map_group():
    group = request.form["group"]
    role_id = request.form["role_id"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO group_mappings (sys_group, role_id) VALUES (?, ?)", (group, role_id))
    conn.commit()
    conn.close()
    flash(f"Mapped group '{group}' to role.", "info")
    return redirect(url_for("roles_bp.list_roles"))
