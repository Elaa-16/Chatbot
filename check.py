import sqlite3

# Try the backend one first — most likely candidate
conn = sqlite3.connect("C:/Users/msi/Chatbot/erp-backend/erp_database.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        report_id TEXT PRIMARY KEY,
        report_type TEXT NOT NULL,
        title TEXT,
        generated_by TEXT,
        generation_date TEXT,
        status TEXT DEFAULT 'Generated',
        FOREIGN KEY (generated_by) REFERENCES employees(employee_id)
    )
""")

conn.commit()
cursor.execute("PRAGMA table_info(reports)")
print(cursor.fetchall())
conn.close()