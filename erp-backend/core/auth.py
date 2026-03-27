from dotenv import load_dotenv
load_dotenv()
import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.hash import argon2
from core.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "❌ JWT_SECRET_KEY environment variable is not set. "
        "Run: export JWT_SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

EMPLOYEE_LOCKED_FIELDS = ["role", "salary_eur", "manager_id", "supervised_employees", "department", "position"]


def build_user_dict(user_data: dict) -> dict:
    return {
        "employee_id": user_data["employee_id"],
        "username":    user_data["username"],
        "role":        user_data["role"],
        "first_name":  user_data["first_name"],
        "last_name":   user_data["last_name"],
        "email":       user_data.get("email"),
        "department":  user_data.get("department"),
        "position":    user_data.get("position"),
        "assigned_projects":    user_data["assigned_projects"].split(";") if user_data["assigned_projects"] else [],
        "supervised_employees": user_data["supervised_employees"].split(";") if user_data["supervised_employees"] else []
    }


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def authenticate_with_token(request: Request, token=Depends(bearer_scheme)):
    # ← removed db=Depends(get_db) — opens own connection instead
    if token and token.credentials:
        payload = verify_token(token.credentials)
        if payload:
            import sqlite3
            conn = sqlite3.connect("erp_database.db", check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM employees WHERE username = ?", (payload["sub"],))
                row = cursor.fetchone()
                if row:
                    return build_user_dict(dict(row))
            finally:
                conn.close()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def check_edit_permission(user: dict):
    if user["role"] not in ["ceo", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO and Managers can create/edit/delete resources"
        )


def get_accessible_projects(user: dict, db):
    if user["role"] in ("ceo", "rh"):
        return None
    cursor = db.cursor()
    if user["role"] == "manager":
        team = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in team])
        # Derive from actual task assignments — never stale
        cursor.execute(
            f"SELECT DISTINCT project_id FROM tasks WHERE assigned_to IN ({placeholders})",
            team
        )
        return [row["project_id"] for row in cursor.fetchall()]
    # employee: use their own assigned_projects
    return user["assigned_projects"] or []


def sync_project_assignments(project: dict, db):
    cursor = db.cursor()
    project_id = project["project_id"]
    role_based = [project.get("project_manager_id"), project.get("site_supervisor_id")]
    assigned_str = project.get("assigned_employees") or ""
    checkbox_assigned = [e for e in assigned_str.split(";") if e]
    all_emp_ids = set(filter(None, role_based + checkbox_assigned))
    for emp_id in all_emp_ids:
        cursor.execute("SELECT assigned_projects FROM employees WHERE employee_id = ?", (emp_id,))
        emp = cursor.fetchone()
        if emp is None:
            continue
        current = emp["assigned_projects"] or ""
        projects_list = [p for p in current.split(";") if p]
        if project_id not in projects_list:
            projects_list.append(project_id)
            cursor.execute(
                "UPDATE employees SET assigned_projects = ? WHERE employee_id = ?",
                (";".join(projects_list), emp_id)
            )
    db.commit()


def log_action(cursor, user_id: str, action: str, entity_type: str, entity_id: str, description: str):
    try:
        from datetime import datetime
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cursor.execute("""
            INSERT INTO activity_logs (log_id, user_id, action_type, entity_type, entity_id, description, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, action, entity_type, entity_id, description, datetime.now().isoformat()))
    except Exception as e:
        print(f"⚠️  Audit log error: {e}")