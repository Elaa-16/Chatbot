"""
Migration: Add password_hash to employees table
Run this once: python migrate_add_passwords.py
"""

import sqlite3
from passlib.hash import argon2

DB_PATH = "erp_database.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add password_hash column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE employees ADD COLUMN password_hash TEXT")
        print("✅ Added password_hash column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️  password_hash column already exists")
        else:
            raise
    
    # 2. Set default password for all users: "demo123"
    default_password = "demo123"
    hashed = argon2.hash(default_password)
    
    cursor.execute("SELECT employee_id, username, role FROM employees")
    employees = cursor.fetchall()
    
    for emp_id, username, role in employees:
        cursor.execute(
            "UPDATE employees SET password_hash = ? WHERE employee_id = ?",
            (hashed, emp_id)
        )
        print(f"✅ Set password for {username} ({role})")
    
    conn.commit()
    conn.close()
    
    print(f"""
╔══════════════════════════════════════════════╗
║         Migration Complete!                  ║
╠══════════════════════════════════════════════╣
║ All users now have password: demo123         ║
║ You can login with any username + demo123    ║
╚══════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    migrate()