#!/usr/bin/env python3

import sqlite3
import os

DB_PATH = "/etc/lnmt/lnmt_stats.db"

def init_db():
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

def list_reservations():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT mac, hostname, ip, notes FROM reservations ORDER BY ip")
    rows = cur.fetchall()
    conn.close()
    print("\nReserved Devices:")
    for mac, hostname, ip, notes in rows:
        print(f"- {mac} -> {ip} ({hostname}) [{notes}]")
    print()

def add_or_update_reservation():
    mac = input("MAC Address (AA:BB:CC:DD:EE:FF): ").strip()
    hostname = input("Hostname: ").strip()
    ip = input("IP Address: ").strip()
    notes = input("Notes (optional): ").strip()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservations (mac, hostname, ip, notes, updated)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(mac) DO UPDATE SET
            hostname = excluded.hostname,
            ip = excluded.ip,
            notes = excluded.notes,
            updated = excluded.updated
    """, (mac, hostname, ip, notes))
    conn.commit()
    conn.close()
    print("[+] Reservation added/updated.\n")

def delete_reservation():
    mac = input("MAC Address to delete: ").strip()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM reservations WHERE mac = ?", (mac,))
    conn.commit()
    conn.close()
    print("[+] Reservation deleted.\n")

def main_menu():
    while True:
        print("=== DNS/DHCP Reservation Menu ===")
        print("1. List reservations")
        print("2. Add or update reservation")
        print("3. Delete reservation")
        print("4. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            list_reservations()
        elif choice == "2":
            add_or_update_reservation()
        elif choice == "3":
            delete_reservation()
        elif choice == "4":
            break
        else:
            print("Invalid choice.\n")

if __name__ == "__main__":
    main_menu()
