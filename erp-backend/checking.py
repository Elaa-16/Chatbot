import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect('erp_database.db')
cur  = conn.cursor()

# Employés qui ont des tâches critiques
cur.execute("SELECT DISTINCT assigned_to FROM tasks WHERE priority='Critical' LIMIT 3")
emp_ids = [r[0] for r in cur.fetchall()]

today     = date.today().isoformat()
end_date  = (date.today() + timedelta(days=5)).isoformat()

for i, eid in enumerate(emp_ids):
    cur.execute("""
        INSERT INTO leave_requests 
        (request_id, employee_id, leave_type, start_date, end_date, 
         total_days, status, requested_date, reason)
        VALUES (?, ?, 'Annual', ?, ?, 5, 'Approved', ?, 'Congé annuel')
    """, (f"LR_DEMO_{i+1}", eid, today, end_date, today))

conn.commit()
conn.close()
print("Congés demo ajoutés")