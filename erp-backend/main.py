from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer
bearer_scheme = HTTPBearer(auto_error=False)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import router as chat_router
from typing import List, Optional
import sqlite3
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import json
from datetime import timedelta
from typing import List, Optional
from jose import JWTError, jwt
from passlib.hash import argon2
from fastapi import Request
from chat import answer_question
import os
import secrets

app = FastAPI(title="Construction ERP API", version="1.0.0")
security = HTTPBasic()
app.include_router(chat_router)

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "❌ JWT_SECRET_KEY environment variable is not set. "
        "Run: export JWT_SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def log_action(cursor, user_id: str, action: str, entity_type: str, entity_id: str, description: str):
    try:
        log_id = f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cursor.execute("""
            INSERT INTO activity_logs (log_id, user_id, action_type, entity_type, entity_id, description, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (log_id, user_id, action, entity_type, entity_id, description, datetime.now().isoformat()))
    except Exception as e:
        print(f"⚠️  Audit log error: {e}")

DB_PATH = "erp_database.db"

def init_reports_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            title TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            generated_by TEXT,
            generation_date TEXT,
            file_path TEXT,
            filters TEXT DEFAULT '{}',
            parameters TEXT DEFAULT '{}',
            status TEXT DEFAULT 'Completed',
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

init_reports_table()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class ProjectCreate(BaseModel):
    project_id: str
    project_name: str
    project_type: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = "Planning"
    budget_eur: Optional[float] = None
    actual_cost_eur: Optional[float] = 0
    completion_percentage: Optional[int] = 0
    location: Optional[str] = None
    project_manager_id: Optional[str] = None
    site_supervisor_id: Optional[str] = None
    description: Optional[str] = None
    assigned_employees: Optional[str] = ""

class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    budget_eur: Optional[float] = None
    actual_cost_eur: Optional[float] = None
    completion_percentage: Optional[int] = None
    location: Optional[str] = None
    project_manager_id: Optional[str] = None
    site_supervisor_id: Optional[str] = None
    description: Optional[str] = None
    assigned_employees: Optional[str] = None

class Project(BaseModel):
    project_id: str
    project_name: str
    project_type: Optional[str]
    client_name: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    status: Optional[str]
    budget_eur: Optional[float]
    actual_cost_eur: Optional[float]
    completion_percentage: Optional[int]
    location: Optional[str]
    description: Optional[str]

class EmployeeCreate(BaseModel):
    employee_id: str
    username: str
    password: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    position: str
    department: str
    role: str
    hire_date: Optional[str] = None
    salary_eur: Optional[float] = None
    manager_id: Optional[str] = None
    supervised_employees: Optional[str] = None
    assigned_projects: Optional[str] = None
    specialization: Optional[str] = None
    certifications: Optional[str] = None
    years_experience: Optional[int] = None

class EmployeeUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    salary_eur: Optional[float] = None
    manager_id: Optional[str] = None
    supervised_employees: Optional[str] = None
    assigned_projects: Optional[str] = None
    specialization: Optional[str] = None
    certifications: Optional[str] = None
    years_experience: Optional[int] = None

class Employee(BaseModel):
    employee_id: str
    username: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    position: str
    department: str
    role: str
    assigned_projects: Optional[str]
    supervised_employees: Optional[str]

class KPICreate(BaseModel):
    kpi_id: str
    project_id: str
    project_name: str
    kpi_date: str
    budget_variance_percentage: Optional[float] = None
    schedule_variance_days: Optional[int] = None
    quality_score: Optional[int] = None
    safety_incidents: Optional[int] = None
    client_satisfaction_score: Optional[float] = None
    team_productivity_percentage: Optional[int] = None
    cost_performance_index: Optional[float] = None
    schedule_performance_index: Optional[float] = None
    risk_level: Optional[str] = None

class KPIUpdate(BaseModel):
    project_name: Optional[str] = None
    kpi_date: Optional[str] = None
    budget_variance_percentage: Optional[float] = None
    schedule_variance_days: Optional[int] = None
    quality_score: Optional[int] = None
    safety_incidents: Optional[int] = None
    client_satisfaction_score: Optional[float] = None
    team_productivity_percentage: Optional[int] = None
    cost_performance_index: Optional[float] = None
    schedule_performance_index: Optional[float] = None
    risk_level: Optional[str] = None

class KPI(BaseModel):
    kpi_id: str
    project_id: str
    project_name: str
    kpi_date: str
    budget_variance_percentage: Optional[float]
    schedule_variance_days: Optional[int]
    quality_score: Optional[int]
    safety_incidents: Optional[int]
    client_satisfaction_score: Optional[float]
    cost_performance_index: Optional[float]
    schedule_performance_index: Optional[float]
    risk_level: Optional[str]
    team_productivity_percentage: Optional[int]

class User(BaseModel):
    employee_id: str
    username: str
    role: str
    assigned_projects: List[str]
    supervised_employees: List[str]

class LeaveRequestCreate(BaseModel):
    request_id: str
    employee_id: str
    employee_name: str
    leave_type: str
    start_date: str
    end_date: str
    total_days: int
    reason: Optional[str] = None

class LeaveRequestUpdate(BaseModel):
    status: Optional[str] = None
    review_comment: Optional[str] = None

class LeaveRequest(BaseModel):
    request_id: str
    employee_id: str
    employee_name: str
    leave_type: str
    start_date: str
    end_date: str
    total_days: int
    reason: Optional[str]
    status: str
    requested_date: str
    reviewed_by: Optional[str]
    reviewed_date: Optional[str]
    review_comment: Optional[str]

class LeaveStats(BaseModel):
    annual_leave_total: int
    annual_leave_taken: int
    annual_leave_remaining: int
    sick_leave_taken: int
    other_leave_taken: int

class TaskCreate(BaseModel):
    task_id: str
    project_id: str
    assigned_to: str
    title: str
    description: Optional[str] = None
    priority: str = "Medium"
    status: str = "Todo"
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    created_by: str

class TaskUpdate(BaseModel):
    assigned_to: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None

class Task(BaseModel):
    task_id: str
    project_id: str
    assigned_to: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[str]
    created_by: str
    created_date: str
    estimated_hours: Optional[float]
    actual_hours: Optional[float]

class DocumentCreate(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    file_path: str
    file_size_kb: Optional[int] = None
    project_id: Optional[str] = None
    uploaded_by: str
    category: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None

class Document(BaseModel):
    document_id: str
    document_name: str
    document_type: str
    file_path: str
    file_size_kb: Optional[int]
    project_id: Optional[str]
    uploaded_by: str
    upload_date: str
    category: Optional[str]
    tags: Optional[str]
    description: Optional[str]

class ActivityLogCreate(BaseModel):
    log_id: str
    user_id: str
    action_type: str
    entity_type: str
    entity_id: str
    description: str
    ip_address: Optional[str] = None

class ActivityLog(BaseModel):
    log_id: str
    user_id: str
    action_type: str
    entity_type: str
    entity_id: str
    description: str
    timestamp: str
    ip_address: Optional[str]

class NotificationCreate(BaseModel):
    notification_id: str
    user_id: str
    notification_type: str
    title: str
    message: str
    priority: str = "Normal"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None

class Notification(BaseModel):
    notification_id: str
    user_id: str
    type: str
    title: str
    message: str
    priority: str
    is_read: bool
    created_date: str
    read_date: Optional[str] = None
    link: Optional[str] = None

class SupplierCreate(BaseModel):
    supplier_id: str
    supplier_name: str
    contact_person: str
    email: str
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Tunisia"
    category: str
    rating: Optional[int] = 3
    status: str = "Active"
    notes: Optional[str] = None

class SupplierUpdate(BaseModel):
    supplier_name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class Supplier(BaseModel):
    supplier_id: str
    supplier_name: str
    contact_person: str
    email: str
    phone: str
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    category: str
    rating: Optional[int]
    status: str
    created_date: str
    notes: Optional[str]

class PurchaseOrderCreate(BaseModel):
    po_id: str
    supplier_id: str
    project_id: str
    order_date: str
    delivery_date: Optional[str] = None
    items_description: str
    total_amount_eur: float
    status: str = "Pending"
    created_by: str
    notes: Optional[str] = None

class PurchaseOrderUpdate(BaseModel):
    delivery_date: Optional[str] = None
    status: Optional[str] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    notes: Optional[str] = None

class PurchaseOrder(BaseModel):
    po_id: str
    supplier_id: str
    project_id: str
    order_date: str
    delivery_date: Optional[str]
    items_description: str
    total_amount_eur: float
    status: str
    created_by: str
    created_date: str
    approved_by: Optional[str]
    approval_date: Optional[str]
    notes: Optional[str]

class TimesheetCreate(BaseModel):
    timesheet_id: str
    employee_id: str
    project_id: str
    work_date: str
    hours_worked: float
    task_description: str
    billable: bool = True
    approved: bool = False
    notes: Optional[str] = None

class TimesheetUpdate(BaseModel):
    hours_worked: Optional[float] = None
    task_description: Optional[str] = None
    billable: Optional[bool] = None
    approved: Optional[bool] = None
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    notes: Optional[str] = None

class Timesheet(BaseModel):
    timesheet_id: str
    employee_id: str
    project_id: str
    work_date: str
    hours_worked: float
    task_description: str
    billable: bool
    approved: bool
    approved_by: Optional[str]
    approval_date: Optional[str]
    submitted_date: str
    notes: Optional[str]

class TimesheetSummary(BaseModel):
    total_hours: float
    billable_hours: float
    non_billable_hours: float
    approved_hours: float
    pending_hours: float

class IssueCreate(BaseModel):
    issue_id: str
    project_id: str
    reported_by: str
    title: str
    description: str
    severity: str = "Medium"
    category: str
    status: str = "Open"
    assigned_to: Optional[str] = None

class Issue(BaseModel):
    issue_id: str
    project_id: str
    reported_by: str
    title: str
    description: str
    severity: str
    category: str
    status: str
    assigned_to: Optional[str]
    created_date: str
    resolved_date: Optional[str]
    resolution_notes: Optional[str]

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_date: Optional[str] = None

class EquipmentCreate(BaseModel):
    equipment_id: str
    name: str
    category: str
    serial_number: str
    status: str = "Available"
    current_project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    location: str
    purchase_date: Optional[str] = None
    purchase_value: Optional[float] = None
    last_maintenance: Optional[str] = None
    next_maintenance: Optional[str] = None
    notes: Optional[str] = None

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    current_project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    location: Optional[str] = None
    last_maintenance: Optional[str] = None
    next_maintenance: Optional[str] = None
    notes: Optional[str] = None

class Equipment(BaseModel):
    equipment_id: str
    name: str
    category: str
    serial_number: str
    status: str
    current_project_id: Optional[str]
    assigned_to: Optional[str]
    location: str
    purchase_date: Optional[str]
    purchase_value: Optional[float]
    last_maintenance: Optional[str]
    next_maintenance: Optional[str]
    notes: Optional[str]

class ReportCreate(BaseModel):
    report_id: str
    report_type: str
    title: str
    period_start: str
    period_end: str
    generated_by: str
    filters: Optional[str] = None
    parameters: Optional[str] = None

class Report(BaseModel):
    report_id: str
    report_type: str
    title: str
    period_start: str
    period_end: str
    generated_by: str
    generation_date: str
    file_path: Optional[str]
    filters: Optional[str]
    parameters: Optional[str]
    status: str
    content: Optional[str] = None


# ============================================================================
# JWT TOKEN FUNCTIONS
# ============================================================================
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
    from datetime import datetime, timedelta, timezone
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

def authenticate_with_token(request: Request, token=Depends(bearer_scheme), db=Depends(get_db)):
    if token and token.credentials:
        payload = verify_token(token.credentials)
        if payload:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM employees WHERE username = ?", (payload["sub"],))
            row = cursor.fetchone()
            if row:
                return build_user_dict(dict(row))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ============================================================================
# AUTHORIZATION HELPERS
# ============================================================================
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


def get_accessible_projects(user: dict, db):
    if user["role"] == "ceo":
        return None
    accessible_projects = set(user["assigned_projects"] or [])
    if user["role"] == "manager":
        cursor = db.cursor()
        for emp_id in user["supervised_employees"]:
            cursor.execute("SELECT assigned_projects FROM employees WHERE employee_id = ?", (emp_id,))
            result = cursor.fetchone()
            if result and result["assigned_projects"]:
                accessible_projects.update([p for p in result["assigned_projects"].split(";") if p])
    return list(accessible_projects)


def check_edit_permission(user: dict):
    if user["role"] not in ["ceo", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CEO and Managers can create/edit/delete resources"
        )


EMPLOYEE_LOCKED_FIELDS = ["role", "salary_eur", "manager_id", "supervised_employees", "department", "position"]


# ============================================================================
# LOGIN
# ============================================================================
@app.post("/login", response_model=LoginResponse)
def login_endpoint(login_data: LoginRequest, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees WHERE username = ?", (login_data.username,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    user_data = dict(row)
    if user_data.get("password_hash"):
        try:
            if not argon2.verify(login_data.password, user_data["password_hash"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    user_obj = build_user_dict(user_data)
    user_obj["must_change_password"] = bool(user_data.get("must_change_password", 0))
    token_data = {"sub": user_data["username"], "employee_id": user_data["employee_id"], "role": user_data["role"]}
    access_token = create_access_token(token_data)
    cursor2 = db.cursor()
    log_action(cursor2, user_data["employee_id"], "Login", "Auth", user_data["employee_id"],
               f"User {user_data['username']} logged in")
    db.commit()
    return {"access_token": access_token, "token_type": "bearer", "user": user_obj}


@app.get("/")
def read_root():
    return {"message": "Construction ERP API", "version": "1.0.0"}


@app.get("/me", response_model=User)
def get_current_user(user: dict = Depends(authenticate_with_token)):
    return User(
        employee_id=user["employee_id"], username=user["username"], role=user["role"],
        assigned_projects=user["assigned_projects"], supervised_employees=user["supervised_employees"]
    )


# ============================================================================
# PROJECTS — avec filtres status pour "en cours / terminés / planification"
# ============================================================================
@app.get("/projects", response_model=List[Project])
def get_projects(
    status: Optional[str] = None,          # "In Progress" | "Completed" | "Planning"
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()

    if accessible_projects is None:
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
    elif not accessible_projects:
        return []
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        query = f"SELECT * FROM projects WHERE project_id IN ({placeholders})"
        params = list(accessible_projects)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY completion_percentage DESC"
    cursor.execute(query, params)
    return [dict(p) for p in cursor.fetchall()]


@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and project_id not in accessible_projects:
        raise HTTPException(status_code=403, detail=f"Access denied to project {project_id}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
    project = cursor.fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(project)


@app.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT project_id FROM projects WHERE project_id = ?", (project.project_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Project ID already exists")
    cursor.execute("""
        INSERT INTO projects (
            project_id, project_name, project_type, client_name, start_date, end_date,
            status, budget_eur, actual_cost_eur, completion_percentage, location,
            project_manager_id, site_supervisor_id, description, assigned_employees
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        project.project_id, project.project_name, project.project_type, project.client_name,
        project.start_date, project.end_date, project.status, project.budget_eur,
        project.actual_cost_eur, project.completion_percentage, project.location,
        project.project_manager_id, project.site_supervisor_id, project.description,
        project.assigned_employees
    ))
    db.commit()
    sync_project_assignments(project.model_dump(), db)
    assigned_str = project.assigned_employees or ""
    all_assigned_ids = set(filter(None, [
        project.project_manager_id, project.site_supervisor_id,
        *[e for e in assigned_str.split(";") if e]
    ]))
    for emp_id in all_assigned_ids:
        try:
            notif_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{emp_id}"
            cursor.execute("""
                INSERT INTO notifications (notification_id, user_id, type, title, message, link, is_read, priority, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (notif_id, emp_id, 'Task', '📁 Nouveau projet assigné',
                  f"Vous avez été assigné au projet: {project.project_name}",
                  '/projects', False, 'High', datetime.now().isoformat()))
        except Exception as e:
            print(f"Notification error for {emp_id}: {e}")
    cursor.execute("SELECT employee_id FROM employees WHERE role = 'ceo' LIMIT 1")
    ceo = cursor.fetchone()
    if ceo and ceo["employee_id"] != user["employee_id"]:
        try:
            notif_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}_CEO"
            cursor.execute("""
                INSERT INTO notifications (notification_id, user_id, type, title, message, link, is_read, priority, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (notif_id, ceo["employee_id"], 'Project', '📁 Nouveau Projet Créé',
                  f"{project.project_name} créé par {user['first_name']} {user['last_name']}",
                  '/projects', 0, 'Normal', datetime.now().isoformat()))
        except Exception as e:
            print(f"CEO notification error: {e}")
    log_action(cursor, user["employee_id"], "Create", "Project", project.project_id,
               f"Created project: {project.project_name}")
    db.commit()
    cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project.project_id,))
    return dict(cursor.fetchone())


@app.put("/projects/{project_id}", response_model=Project)
def update_project(project_id: str, project_update: ProjectUpdate,
                   user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = dict(row)
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_fields = [f"{field} = ?" for field in update_data]
    update_values = list(update_data.values()) + [project_id]
    cursor.execute(f"UPDATE projects SET {', '.join(update_fields)} WHERE project_id = ?", update_values)
    db.commit()
    merged = {**existing, **update_data, "project_id": project_id}
    sync_project_assignments(merged, db)
    log_action(cursor, user["employee_id"], "Update", "Project", project_id,
               f"Updated project: {project_id}")
    db.commit()
    cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
    return dict(cursor.fetchone())


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT project_id FROM projects WHERE project_id = ?", (project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")
    cursor.execute("DELETE FROM kpis WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
    log_action(cursor, user["employee_id"], "Delete", "Project", project_id, f"Deleted project {project_id}")
    db.commit()
    return None


# ============================================================================
# EMPLOYEES — filtres: department, role, employee_id
# ============================================================================
@app.get("/employees", response_model=List[Employee])
def get_employees(
    department: Optional[str] = None,   # "Finance"|"Projects"|"Operations"|"Human Resources"|"IT"|"Executive"
    role: Optional[str] = None,         # "ceo"|"manager"|"employee"|"rh"
    employee_id: Optional[str] = None,  # filtre exact par ID
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    if user["role"] in ("ceo", "rh"):
        query = "SELECT * FROM employees WHERE 1=1"
        params = []
    elif user["role"] == "manager":
        supervised = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in supervised])
        query = f"SELECT * FROM employees WHERE employee_id IN ({placeholders})"
        params = list(supervised)
    else:
        query = "SELECT * FROM employees WHERE employee_id = ?"
        params = [user["employee_id"]]

    if department:
        query += " AND department = ?"
        params.append(department)
    if role:
        query += " AND role = ?"
        params.append(role)
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)

    query += " ORDER BY last_name ASC"
    cursor.execute(query, params)
    return [dict(emp) for emp in cursor.fetchall()]


@app.get("/employees/{employee_id}", response_model=Employee)
def get_employee(employee_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] == "employee" and employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only view your own information")
    if user["role"] == "manager":
        allowed_ids = user["supervised_employees"] + [user["employee_id"]]
        if employee_id not in allowed_ids:
            raise HTTPException(status_code=403, detail="You can only view your team's information")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    employee = cursor.fetchone()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(employee)


@app.post("/employees", response_model=Employee, status_code=status.HTTP_201_CREATED)
def create_employee(employee: EmployeeCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] != "ceo":
        raise HTTPException(status_code=403, detail="Only CEO can create employees")
    cursor = db.cursor()
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id = ? OR username = ?",
                   (employee.employee_id, employee.username))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Employee ID or username already exists")
    password_hash = argon2.hash(employee.password)
    cursor.execute("""
        INSERT INTO employees (
            employee_id, username, password_hash, first_name, last_name, email, phone,
            position, department, role, hire_date, salary_eur, manager_id,
            supervised_employees, assigned_projects, specialization, certifications, years_experience
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        employee.employee_id, employee.username, password_hash,
        employee.first_name, employee.last_name, employee.email, employee.phone,
        employee.position, employee.department, employee.role, employee.hire_date,
        employee.salary_eur, employee.manager_id, employee.supervised_employees,
        employee.assigned_projects, employee.specialization, employee.certifications,
        employee.years_experience
    ))
    log_action(cursor, user["employee_id"], "Create", "Employee", employee.employee_id,
               f"Created employee: {employee.username} (role: {employee.role})")
    db.commit()
    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee.employee_id,))
    return dict(cursor.fetchone())


@app.put("/employees/{employee_id}", response_model=Employee)
def update_employee(employee_id: str, employee_update: EmployeeUpdate,
                    user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] == "employee" and employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only update your own information")
    if user["role"] == "manager" and employee_id not in user["supervised_employees"] and employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only update your team members")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Employee not found")
    update_fields, update_values = [], []
    for field, value in employee_update.model_dump(exclude_unset=True).items():
        if user["role"] == "employee" and field in EMPLOYEE_LOCKED_FIELDS:
            continue
        if user["role"] == "manager" and field in ["role", "salary_eur"]:
            continue
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No permitted fields to update")
    update_values.append(employee_id)
    cursor.execute(f"UPDATE employees SET {', '.join(update_fields)} WHERE employee_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Employee", employee_id,
               f"Updated employee {employee_id}")
    db.commit()
    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    return dict(cursor.fetchone())


@app.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] != "ceo":
        raise HTTPException(status_code=403, detail="Only CEO can delete employees")
    if employee_id == user["employee_id"]:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
    cursor = db.cursor()
    cursor.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Employee not found")
    cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
    log_action(cursor, user["employee_id"], "Delete", "Employee", employee_id, f"Deleted employee {employee_id}")
    db.commit()
    return None


# ============================================================================
# KPIS — filtres: delayed, over_budget, risk_level, project_id, spi_max, cpi_max
# ============================================================================
@app.get("/kpis", response_model=List[KPI])
def get_kpis(
    delayed: Optional[bool] = None,         # True → schedule_variance_days > 0
    over_budget: Optional[bool] = None,     # True → budget_variance_percentage > 0
    risk_level: Optional[str] = None,       # "High" | "Medium" | "Low"
    project_id: Optional[str] = None,       # filtre par projet
    spi_max: Optional[float] = None,        # SPI < spi_max (ex: 0.8)
    cpi_max: Optional[float] = None,        # CPI < cpi_max
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()

    if accessible_projects is None:
        query = "SELECT * FROM kpis WHERE 1=1"
        params = []
    elif not accessible_projects:
        return []
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        query = f"SELECT * FROM kpis WHERE project_id IN ({placeholders})"
        params = list(accessible_projects)

    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if delayed is True:
        query += " AND schedule_variance_days > 0"
    if over_budget is True:
        query += " AND budget_variance_percentage > 0"
    if risk_level:
        query += " AND risk_level = ?"
        params.append(risk_level)
    if spi_max is not None:
        query += " AND schedule_performance_index < ?"
        params.append(spi_max)
    if cpi_max is not None:
        query += " AND cost_performance_index < ?"
        params.append(cpi_max)

    query += " ORDER BY kpi_date DESC"
    cursor.execute(query, params)
    return [dict(k) for k in cursor.fetchall()]


@app.get("/kpis/project/{project_id}", response_model=List[KPI])
def get_project_kpis(project_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and project_id not in accessible_projects:
        raise HTTPException(status_code=403, detail=f"Access denied to KPIs for project {project_id}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM kpis WHERE project_id = ? ORDER BY kpi_date DESC", (project_id,))
    return [dict(k) for k in cursor.fetchall()]


@app.get("/kpis/{kpi_id}", response_model=KPI)
def get_kpi(kpi_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM kpis WHERE kpi_id = ?", (kpi_id,))
    kpi = cursor.fetchone()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and kpi["project_id"] not in accessible_projects:
        raise HTTPException(status_code=403, detail="Access denied")
    return dict(kpi)


@app.post("/kpis", response_model=KPI, status_code=status.HTTP_201_CREATED)
def create_kpi(kpi: KPICreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT kpi_id FROM kpis WHERE kpi_id = ?", (kpi.kpi_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="KPI ID already exists")
    cursor.execute("SELECT project_id FROM projects WHERE project_id = ?", (kpi.project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="Project not found")
    cursor.execute("""
        INSERT INTO kpis (
            kpi_id, project_id, project_name, kpi_date, budget_variance_percentage,
            schedule_variance_days, quality_score, safety_incidents, client_satisfaction_score,
            team_productivity_percentage, cost_performance_index, schedule_performance_index, risk_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kpi.kpi_id, kpi.project_id, kpi.project_name, kpi.kpi_date, kpi.budget_variance_percentage,
        kpi.schedule_variance_days, kpi.quality_score, kpi.safety_incidents, kpi.client_satisfaction_score,
        kpi.team_productivity_percentage, kpi.cost_performance_index, kpi.schedule_performance_index, kpi.risk_level
    ))
    log_action(cursor, user["employee_id"], "Create", "KPI", kpi.kpi_id, f"Created KPI for project {kpi.project_id}")
    db.commit()
    cursor.execute("SELECT * FROM kpis WHERE kpi_id = ?", (kpi.kpi_id,))
    return dict(cursor.fetchone())


@app.put("/kpis/{kpi_id}", response_model=KPI)
def update_kpi(kpi_id: str, kpi_update: KPIUpdate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM kpis WHERE kpi_id = ?", (kpi_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="KPI not found")
    update_fields, update_values = [], []
    for field, value in kpi_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(kpi_id)
    cursor.execute(f"UPDATE kpis SET {', '.join(update_fields)} WHERE kpi_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "KPI", kpi_id, f"Updated KPI {kpi_id}")
    db.commit()
    cursor.execute("SELECT * FROM kpis WHERE kpi_id = ?", (kpi_id,))
    return dict(cursor.fetchone())


@app.delete("/kpis/{kpi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kpi(kpi_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT kpi_id FROM kpis WHERE kpi_id = ?", (kpi_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="KPI not found")
    cursor.execute("DELETE FROM kpis WHERE kpi_id = ?", (kpi_id,))
    log_action(cursor, user["employee_id"], "Delete", "KPI", kpi_id, f"Deleted KPI {kpi_id}")
    db.commit()
    return None


# ============================================================================
# STATISTICS
# ============================================================================
@app.get("/stats/summary")
def get_summary_stats(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()
    if accessible_projects is None:
        cursor.execute("""
            SELECT COUNT(*) as total_projects, SUM(budget_eur) as total_budget,
                   SUM(actual_cost_eur) as total_actual_cost, AVG(completion_percentage) as avg_completion
            FROM projects
        """)
    elif not accessible_projects:
        return {"total_projects": 0, "total_budget": 0, "total_actual_cost": 0, "avg_completion": 0}
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        cursor.execute(f"""
            SELECT COUNT(*) as total_projects, SUM(budget_eur) as total_budget,
                   SUM(actual_cost_eur) as total_actual_cost, AVG(completion_percentage) as avg_completion
            FROM projects WHERE project_id IN ({placeholders})
        """, accessible_projects)
    return dict(cursor.fetchone())


# ============================================================================
# LEAVE REQUESTS — filtres: status, employee_id, leave_type, start_date, end_date
# active_today est géré côté RAG (post-API)
# ============================================================================
@app.get("/leave-requests", response_model=List[LeaveRequest])
def get_leave_requests(
    status: Optional[str] = None,          # "Approved"|"Pending"|"Rejected"|"Cancelled"
    employee_id: Optional[str] = None,     # filtre par employé
    leave_type: Optional[str] = None,      # "Annual"|"Sick"|"Emergency"|"Maternity"|"Other"
    start_date: Optional[str] = None,      # congés démarrant après cette date (YYYY-MM-DD)
    end_date: Optional[str] = None,        # congés se terminant avant cette date (YYYY-MM-DD)
    year: Optional[int] = None,            # filtre par année (sur requested_date)
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()

    # RBAC base
    if user["role"] in ("ceo", "rh"):
        query = "SELECT * FROM leave_requests WHERE 1=1"
        params = []
    elif user["role"] == "manager":
        supervised = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in supervised])
        query = f"SELECT * FROM leave_requests WHERE employee_id IN ({placeholders})"
        params = list(supervised)
    else:
        query = "SELECT * FROM leave_requests WHERE employee_id = ?"
        params = [user["employee_id"]]

    # Filtres optionnels
    if status:
        query += " AND status = ?"
        params.append(status)
    if employee_id:
        # Sécurité : un employee ne peut filtrer que sur lui-même
        if user["role"] == "employee" and employee_id != user["employee_id"]:
            return []
        query += " AND employee_id = ?"
        params.append(employee_id)
    if leave_type:
        query += " AND leave_type = ?"
        params.append(leave_type)
    if start_date:
        query += " AND end_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND start_date <= ?"
        params.append(end_date)
    if year:
        query += " AND strftime('%Y', requested_date) = ?"
        params.append(str(year))

    query += " ORDER BY requested_date DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]


@app.get("/leave-requests/pending", response_model=List[LeaveRequest])
def get_pending_leave_requests(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] == "ceo":
        cursor.execute("""
            SELECT lr.* FROM leave_requests lr
            JOIN employees e ON lr.employee_id = e.employee_id
            WHERE lr.status = 'Pending' AND e.role = 'manager'
            ORDER BY lr.requested_date ASC
        """)
    elif user["role"] == "rh":
        cursor.execute("SELECT * FROM leave_requests WHERE status = 'Pending' ORDER BY requested_date ASC")
    elif user["role"] == "manager":
        supervised = user["supervised_employees"]
        if not supervised:
            return []
        placeholders = ','.join(['?' for _ in supervised])
        cursor.execute(f"SELECT * FROM leave_requests WHERE employee_id IN ({placeholders}) AND status = 'Pending' ORDER BY requested_date ASC", supervised)
    else:
        return []
    return [dict(r) for r in cursor.fetchall()]


@app.get("/leave-requests/{request_id}", response_model=LeaveRequest)
def get_leave_request(request_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    request = cursor.fetchone()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if user["role"] == "employee" and request["employee_id"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == "manager":
        if request["employee_id"] not in user["supervised_employees"] and request["employee_id"] != user["employee_id"]:
            raise HTTPException(status_code=403, detail="Access denied")
    return dict(request)


@app.post("/leave-requests", response_model=LeaveRequest, status_code=status.HTTP_201_CREATED)
def create_leave_request(leave_request: LeaveRequestCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] in ("ceo", "rh"):
        raise HTTPException(status_code=403, detail="RH/CEO do not submit leave requests")
    if user["role"] == "employee" and leave_request.employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only submit leave requests for yourself")
    cursor.execute("SELECT request_id FROM leave_requests WHERE request_id = ?", (leave_request.request_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Request ID already exists")
    if leave_request.leave_type == "Annual":
        cursor.execute("SELECT annual_leave_total, annual_leave_taken FROM employees WHERE employee_id = ?", (leave_request.employee_id,))
        emp_leave = cursor.fetchone()
        if emp_leave:
            remaining = emp_leave["annual_leave_total"] - emp_leave["annual_leave_taken"]
            if leave_request.total_days > remaining:
                raise HTTPException(status_code=400, detail=f"Insufficient annual leave. Remaining: {remaining} days")
    cursor.execute("""
        INSERT INTO leave_requests (request_id, employee_id, employee_name, leave_type, start_date, end_date,
            total_days, reason, status, requested_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (
        leave_request.request_id, leave_request.employee_id, leave_request.employee_name,
        leave_request.leave_type, leave_request.start_date, leave_request.end_date,
        leave_request.total_days, leave_request.reason, datetime.now().isoformat()
    ))
    cursor.execute("SELECT role, manager_id FROM employees WHERE employee_id = ?", (leave_request.employee_id,))
    requester = cursor.fetchone()
    approver_id = None
    if requester:
        if requester["role"] == "employee":
            approver_id = requester["manager_id"]
        elif requester["role"] == "manager":
            cursor.execute("SELECT employee_id FROM employees WHERE role = 'ceo' LIMIT 1")
            ceo = cursor.fetchone()
            if ceo:
                approver_id = ceo["employee_id"]
    if approver_id:
        notification_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, notification_type, title, message,
                priority, is_read, created_date, related_entity_type, related_entity_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification_id, approver_id, 'Leave', 'Nouvelle demande de congé',
            f"{leave_request.employee_name} a demandé {leave_request.total_days} jour(s) ({leave_request.leave_type}) "
            f"du {leave_request.start_date} au {leave_request.end_date}",
            'High', 0, datetime.now().isoformat(), 'leave_request', leave_request.request_id
        ))
    db.commit()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (leave_request.request_id,))
    return dict(cursor.fetchone())


@app.put("/leave-requests/{request_id}/approve", response_model=LeaveRequest)
def approve_leave_request(request_id: str, review_comment: Optional[str] = None,
                           user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    request = cursor.fetchone()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    can_approve = user["role"] == "rh" or (user["role"] == "manager" and request["employee_id"] in user["supervised_employees"])
    if not can_approve:
        raise HTTPException(status_code=403, detail="You don't have permission to approve this request")
    cursor.execute("""
        UPDATE leave_requests SET status = 'Approved', reviewed_by = ?, reviewed_date = ?, review_comment = ?
        WHERE request_id = ?
    """, (user["employee_id"], datetime.now().isoformat(), review_comment, request_id))
    if request["leave_type"] == "Annual":
        cursor.execute("UPDATE employees SET annual_leave_taken = annual_leave_taken + ? WHERE employee_id = ?",
                       (request["total_days"], request["employee_id"]))
    elif request["leave_type"] == "Sick":
        cursor.execute("UPDATE employees SET sick_leave_taken = sick_leave_taken + ? WHERE employee_id = ?",
                       (request["total_days"], request["employee_id"]))
    else:
        cursor.execute("UPDATE employees SET other_leave_taken = other_leave_taken + ? WHERE employee_id = ?",
                       (request["total_days"], request["employee_id"]))
    notification_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cursor.execute("""
        INSERT INTO notifications (notification_id, user_id, type, title, message, priority, is_read, created_date, related_entity_type, related_entity_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (notification_id, request["employee_id"], 'Leave', '✅ Congé approuvé',
          f"Votre demande de congé ({request['total_days']} jours) a été approuvée",
          'Medium', 0, datetime.now().isoformat(), 'leave_request', request_id))
    log_action(cursor, user["employee_id"], "Approve", "LeaveRequest", request_id,
               f"Approved leave request for {request['employee_id']}")
    db.commit()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    return dict(cursor.fetchone())


@app.put("/leave-requests/{request_id}/reject", response_model=LeaveRequest)
def reject_leave_request(request_id: str, review_comment: str,
                          user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    request = cursor.fetchone()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    can_reject = user["role"] == "rh" or (user["role"] == "manager" and request["employee_id"] in user["supervised_employees"])
    if not can_reject:
        raise HTTPException(status_code=403, detail="You don't have permission to reject this request")
    cursor.execute("""
        UPDATE leave_requests SET status = 'Rejected', reviewed_by = ?, reviewed_date = ?, review_comment = ?
        WHERE request_id = ?
    """, (user["employee_id"], datetime.now().isoformat(), review_comment, request_id))
    notification_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cursor.execute("""
        INSERT INTO notifications (notification_id, user_id, notification_type, title, message, priority, is_read, created_date, related_entity_type, related_entity_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (notification_id, request["employee_id"], 'Leave', '❌ Congé rejeté',
          f"Votre demande de congé a été rejetée. Raison: {review_comment}",
          'High', 0, datetime.now().isoformat(), 'leave_request', request_id))
    log_action(cursor, user["employee_id"], "Reject", "LeaveRequest", request_id,
               f"Rejected leave request for {request['employee_id']}: {review_comment}")
    db.commit()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    return dict(cursor.fetchone())


@app.put("/leave-requests/{request_id}/cancel", response_model=LeaveRequest)
def cancel_leave_request(request_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    request = cursor.fetchone()
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if request["employee_id"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only cancel your own requests")
    if request["status"] != "Pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
    cursor.execute("UPDATE leave_requests SET status = 'Cancelled' WHERE request_id = ?", (request_id,))
    db.commit()
    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
    return dict(cursor.fetchone())


@app.get("/employees/{employee_id}/leave-stats", response_model=LeaveStats)
def get_employee_leave_stats(employee_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] == "employee" and employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if user["role"] == "manager" and employee_id not in user["supervised_employees"] and employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    cursor = db.cursor()
    cursor.execute("SELECT annual_leave_total, annual_leave_taken, sick_leave_taken, other_leave_taken FROM employees WHERE employee_id = ?", (employee_id,))
    stats = cursor.fetchone()
    if not stats:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "annual_leave_total":     stats["annual_leave_total"],
        "annual_leave_taken":     stats["annual_leave_taken"],
        "annual_leave_remaining": stats["annual_leave_total"] - stats["annual_leave_taken"],
        "sick_leave_taken":       stats["sick_leave_taken"],
        "other_leave_taken":      stats["other_leave_taken"]
    }


# ============================================================================
# TASKS — filtres: status, priority, assigned_to, project_id, overdue
# ============================================================================
@app.get("/tasks", response_model=List[Task])
def get_tasks(
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,          # "Todo"|"In Progress"|"Done"|"Blocked"
    priority: Optional[str] = None,        # "Critical"|"High"|"Medium"|"Low"
    overdue: Optional[bool] = None,        # True → due_date < today AND status != Done
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None:
        if not accessible_projects:
            return []
        placeholders = ','.join(['?' for _ in accessible_projects])
        query += f" AND project_id IN ({placeholders})"
        params.extend(accessible_projects)

    if user.get("role") == "employee":
        query += " AND assigned_to = ?"
        params.append(user.get("employee_id"))
    elif user.get("role") == "manager":
        team = user.get("supervised_employees", []) + [user.get("employee_id")]
        placeholders_team = ','.join(['?' for _ in team])
        query += f" AND assigned_to IN ({placeholders_team})"
        params.extend(team)
        if assigned_to and assigned_to in team:
            query += " AND assigned_to = ?"
            params.append(assigned_to)
    else:
        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)

    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if overdue is True:
        today = date.today().isoformat()
        query += " AND due_date < ? AND status != 'Done'"
        params.append(today)

    query += " ORDER BY due_date ASC, priority DESC"
    cursor.execute(query, params)
    return [dict(t) for t in cursor.fetchall()]


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.get("role") == "employee" and task["assigned_to"] != user.get("employee_id"):
        raise HTTPException(status_code=403, detail="Access denied")
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and task["project_id"] not in accessible_projects:
        raise HTTPException(status_code=403, detail="Access denied")
    return dict(task)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task.task_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Task ID already exists")
    cursor.execute("SELECT project_id FROM projects WHERE project_id = ?", (task.project_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=400, detail="Project not found")
    cursor.execute("""
        INSERT INTO tasks (task_id, project_id, assigned_to, title, description, priority, status,
            due_date, created_by, created_date, estimated_hours, actual_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task.task_id, task.project_id, task.assigned_to, task.title, task.description,
        task.priority, task.status, task.due_date, task.created_by,
        datetime.now().isoformat(), task.estimated_hours, 0
    ))
    try:
        notification_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, type, title, message, link, is_read, priority, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification_id, task.assigned_to, 'Task', 'Nouvelle tâche assignée',
            f"Vous avez été assigné à la tâche: {task.title} (Priorité: {task.priority})",
            '/tasks', False, 'High' if task.priority in ['Critical', 'High'] else 'Medium',
            datetime.now().isoformat()
        ))
    except Exception as e:
        print(f"⚠️  Notification non créée: {e}")
    log_action(cursor, user["employee_id"], "Create", "Task", task.task_id,
               f"Created task: {task.title} on project {task.project_id}")
    db.commit()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task.task_id,))
    return dict(cursor.fetchone())


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: str, task_update: TaskUpdate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Task not found")
    update_fields, update_values = [], []
    for field, value in task_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(task_id)
    cursor.execute(f"UPDATE tasks SET {', '.join(update_fields)} WHERE task_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Task", task_id, f"Updated task {task_id}")
    db.commit()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    return dict(cursor.fetchone())


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    log_action(cursor, user["employee_id"], "Delete", "Task", task_id, f"Deleted task {task_id}")
    db.commit()
    return None


@app.put("/tasks/{task_id}/status")
def update_task_status(task_id: str, new_status: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
    log_action(cursor, user["employee_id"], "Update", "Task", task_id, f"Status changed to {new_status}")
    db.commit()
    return {"message": "Status updated", "task_id": task_id, "new_status": new_status}


# ============================================================================
# ISSUES — filtres: severity, status, category, project_id
# ============================================================================
@app.get("/issues", response_model=List[Issue])
def get_issues(
    project_id: Optional[str] = None,
    severity: Optional[str] = None,    # "Critical"|"High"|"Medium"|"Low"
    status: Optional[str] = None,      # "Open"|"In Progress"|"Resolved"|"Closed"
    category: Optional[str] = None,    # "Safety"|"Quality"|"Delay"|"Budget"|"Technical"|"Other"
    unresolved: Optional[bool] = None, # True → status IN (Open, In Progress)
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM issues WHERE 1=1"
    params = []
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None:
        if not accessible_projects:
            return []
        placeholders = ','.join(['?' for _ in accessible_projects])
        query += f" AND project_id IN ({placeholders})"
        params.extend(accessible_projects)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if unresolved is True:
        query += " AND status IN ('Open', 'In Progress')"
    query += " ORDER BY created_date DESC, severity DESC"
    cursor.execute(query, params)
    return [dict(i) for i in cursor.fetchall()]


@app.post("/issues", response_model=Issue, status_code=status.HTTP_201_CREATED)
def create_issue(issue: IssueCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT issue_id FROM issues WHERE issue_id = ?", (issue.issue_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Issue ID already exists")
    cursor.execute("""
        INSERT INTO issues (issue_id, project_id, reported_by, title, description, severity, category,
            status, assigned_to, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        issue.issue_id, issue.project_id, issue.reported_by, issue.title, issue.description,
        issue.severity, issue.category, issue.status, issue.assigned_to,
        datetime.now().isoformat()
    ))
    cursor.execute("SELECT employee_id FROM employees WHERE role = 'ceo' LIMIT 1")
    ceo = cursor.fetchone()
    if ceo:
        notif_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        priority = 'High' if issue.severity in ('Critical', 'High') else 'Normal'
        icon = '🚨' if issue.severity == 'Critical' else '⚠️'
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, type, title, message, link, is_read, priority, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (notif_id, ceo["employee_id"], 'Issue',
              f"{icon} Nouvel Incident {issue.severity}",
              f"{issue.title} — Projet: {issue.project_id} — Catégorie: {issue.category}",
              '/issues', 0, priority, datetime.now().isoformat()))
    log_action(cursor, user["employee_id"], "Create", "Issue", issue.issue_id,
               f"Reported issue: {issue.title} (severity: {issue.severity})")
    db.commit()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue.issue_id,))
    return dict(cursor.fetchone())


@app.put("/issues/{issue_id}", response_model=Issue)
def update_issue(issue_id: str, issue_update: IssueUpdate,
                 user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Issue not found")
    update_fields, update_values = [], []
    for field, value in issue_update.model_dump(exclude_unset=True).items():
        if field == "location":
            continue
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(issue_id)
    cursor.execute(f"UPDATE issues SET {', '.join(update_fields)} WHERE issue_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Issue", issue_id, f"Updated issue {issue_id}")
    db.commit()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id,))
    return dict(cursor.fetchone())


@app.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(issue_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT issue_id FROM issues WHERE issue_id = ?", (issue_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Issue not found")
    cursor.execute("DELETE FROM issues WHERE issue_id = ?", (issue_id,))
    log_action(cursor, user["employee_id"], "Delete", "Issue", issue_id, f"Deleted issue {issue_id}")
    db.commit()
    return None


# ============================================================================
# EQUIPMENT — filtres: status, category, current_project_id
# ============================================================================
@app.get("/equipment", response_model=List[Equipment])
def get_equipment(
    status: Optional[str] = None,              # "Available"|"In Use"|"Maintenance"
    category: Optional[str] = None,
    current_project_id: Optional[str] = None,
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM equipment WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    if current_project_id:
        query += " AND current_project_id = ?"
        params.append(current_project_id)
    query += " ORDER BY name ASC"
    cursor.execute(query, params)
    return [dict(eq) for eq in cursor.fetchall()]


@app.get("/equipment/available", response_model=List[Equipment])
def get_available_equipment(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment WHERE status = 'Available' ORDER BY name ASC")
    return [dict(eq) for eq in cursor.fetchall()]


@app.post("/equipment", response_model=Equipment, status_code=status.HTTP_201_CREATED)
def create_equipment(equipment: EquipmentCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT equipment_id FROM equipment WHERE equipment_id = ?", (equipment.equipment_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Equipment ID already exists")
    cursor.execute("""
        INSERT INTO equipment (equipment_id, name, category, serial_number, status, current_project_id,
            assigned_to, location, purchase_date, purchase_value, last_maintenance, next_maintenance, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        equipment.equipment_id, equipment.name, equipment.category, equipment.serial_number,
        equipment.status, equipment.current_project_id, equipment.assigned_to, equipment.location,
        equipment.purchase_date, equipment.purchase_value, equipment.last_maintenance,
        equipment.next_maintenance, equipment.notes
    ))
    log_action(cursor, user["employee_id"], "Create", "Equipment", equipment.equipment_id,
               f"Added equipment: {equipment.name}")
    db.commit()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment.equipment_id,))
    return dict(cursor.fetchone())


@app.put("/equipment/{equipment_id}", response_model=Equipment)
def update_equipment(equipment_id: str, equipment_update: EquipmentUpdate,
                     user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Equipment not found")
    update_fields, update_values = [], []
    for field, value in equipment_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(equipment_id)
    cursor.execute(f"UPDATE equipment SET {', '.join(update_fields)} WHERE equipment_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Equipment", equipment_id, f"Updated equipment {equipment_id}")
    db.commit()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
    return dict(cursor.fetchone())


@app.put("/equipment/{equipment_id}/assign")
def assign_equipment(equipment_id: str, project_id: str, assigned_to: str,
                     user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
    equipment = cursor.fetchone()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    if equipment["status"] != "Available":
        raise HTTPException(status_code=400, detail="Equipment is not available")
    cursor.execute("UPDATE equipment SET status = 'In Use', current_project_id = ?, assigned_to = ? WHERE equipment_id = ?",
                   (project_id, assigned_to, equipment_id))
    log_action(cursor, user["employee_id"], "Update", "Equipment", equipment_id,
               f"Assigned equipment {equipment_id} to project {project_id}")
    db.commit()
    return {"message": "Equipment assigned successfully", "equipment_id": equipment_id}


@app.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT equipment_id FROM equipment WHERE equipment_id = ?", (equipment_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Equipment not found")
    cursor.execute("DELETE FROM equipment WHERE equipment_id = ?", (equipment_id,))
    log_action(cursor, user["employee_id"], "Delete", "Equipment", equipment_id, f"Deleted equipment {equipment_id}")
    db.commit()
    return None


# ============================================================================
# SUPPLIERS — filtres: category, status, sort_by_rating
# ============================================================================
@app.get("/suppliers", response_model=List[Supplier])
def get_suppliers(
    category: Optional[str] = None,
    status: Optional[str] = None,          # "Active"|"Inactive"
    search: Optional[str] = None,
    sort_by_rating: Optional[bool] = None, # True → ORDER BY rating DESC
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (supplier_name LIKE ? OR contact_person LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if sort_by_rating:
        query += " ORDER BY rating DESC"
    else:
        query += " ORDER BY supplier_name ASC"
    cursor.execute(query, params)
    return [dict(s) for s in cursor.fetchall()]


@app.post("/suppliers", response_model=Supplier, status_code=status.HTTP_201_CREATED)
def create_supplier(supplier: SupplierCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT supplier_id FROM suppliers WHERE supplier_id = ?", (supplier.supplier_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Supplier ID already exists")
    cursor.execute("""
        INSERT INTO suppliers (supplier_id, supplier_name, contact_person, email, phone, address, city,
            country, category, rating, status, created_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        supplier.supplier_id, supplier.supplier_name, supplier.contact_person, supplier.email,
        supplier.phone, supplier.address, supplier.city, supplier.country, supplier.category,
        supplier.rating, supplier.status, datetime.now().isoformat(), supplier.notes
    ))
    log_action(cursor, user["employee_id"], "Create", "Supplier", supplier.supplier_id,
               f"Created supplier: {supplier.supplier_name}")
    db.commit()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier.supplier_id,))
    return dict(cursor.fetchone())


@app.put("/suppliers/{supplier_id}", response_model=Supplier)
def update_supplier(supplier_id: str, supplier_update: SupplierUpdate,
                    user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Supplier not found")
    update_fields, update_values = [], []
    for field, value in supplier_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(supplier_id)
    cursor.execute(f"UPDATE suppliers SET {', '.join(update_fields)} WHERE supplier_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Supplier", supplier_id, f"Updated supplier {supplier_id}")
    db.commit()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    return dict(cursor.fetchone())


@app.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT supplier_id FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Supplier not found")
    cursor.execute("DELETE FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    log_action(cursor, user["employee_id"], "Delete", "Supplier", supplier_id, f"Deleted supplier {supplier_id}")
    db.commit()
    return None


# ============================================================================
# PURCHASE ORDERS
# ============================================================================
@app.get("/purchase-orders", response_model=List[PurchaseOrder])
def get_purchase_orders(project_id: Optional[str] = None, supplier_id: Optional[str] = None,
                        status: Optional[str] = None, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM purchase_orders WHERE 1=1"
    params = []
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None:
        if not accessible_projects:
            return []
        placeholders = ','.join(['?' for _ in accessible_projects])
        query += f" AND project_id IN ({placeholders})"
        params.extend(accessible_projects)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if supplier_id:
        query += " AND supplier_id = ?"
        params.append(supplier_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY order_date DESC"
    cursor.execute(query, params)
    return [dict(o) for o in cursor.fetchall()]


@app.post("/purchase-orders", response_model=PurchaseOrder, status_code=status.HTTP_201_CREATED)
def create_purchase_order(po: PurchaseOrderCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT po_id FROM purchase_orders WHERE po_id = ?", (po.po_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Purchase order ID already exists")
    cursor.execute("""
        INSERT INTO purchase_orders (po_id, supplier_id, project_id, order_date, delivery_date, items_description,
            total_amount_eur, status, created_by, created_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        po.po_id, po.supplier_id, po.project_id, po.order_date, po.delivery_date,
        po.items_description, po.total_amount_eur, po.status, po.created_by,
        datetime.now().isoformat(), po.notes
    ))
    log_action(cursor, user["employee_id"], "Create", "PurchaseOrder", po.po_id,
               f"Created PO {po.po_id} for project {po.project_id}")
    db.commit()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po.po_id,))
    return dict(cursor.fetchone())


@app.put("/purchase-orders/{po_id}", response_model=PurchaseOrder)
def update_purchase_order(po_id: str, po_update: PurchaseOrderUpdate,
                          user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Purchase order not found")
    update_fields, update_values = [], []
    for field, value in po_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(po_id)
    cursor.execute(f"UPDATE purchase_orders SET {', '.join(update_fields)} WHERE po_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "PurchaseOrder", po_id, f"Updated PO {po_id}")
    db.commit()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    return dict(cursor.fetchone())


@app.delete("/purchase-orders/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(po_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT po_id FROM purchase_orders WHERE po_id = ?", (po_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Purchase order not found")
    cursor.execute("DELETE FROM purchase_orders WHERE po_id = ?", (po_id,))
    log_action(cursor, user["employee_id"], "Delete", "PurchaseOrder", po_id, f"Deleted PO {po_id}")
    db.commit()
    return None


# ============================================================================
# TIMESHEETS — filtres: employee_id, project_id, approved, date_from, date_to
# ============================================================================
@app.get("/timesheets", response_model=List[Timesheet])
def get_timesheets(
    employee_id: Optional[str] = None,
    project_id: Optional[str] = None,
    approved: Optional[bool] = None,
    date_from: Optional[str] = None,   # YYYY-MM-DD
    date_to: Optional[str] = None,     # YYYY-MM-DD
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
    query = "SELECT * FROM timesheets WHERE 1=1"
    params = []
    if user["role"] == "employee":
        query += " AND employee_id = ?"
        params.append(user["employee_id"])
    elif user["role"] == "manager":
        supervised = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in supervised])
        query += f" AND employee_id IN ({placeholders})"
        params.extend(supervised)
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if approved is not None:
        query += " AND approved = ?"
        params.append(approved)
    if date_from:
        query += " AND work_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND work_date <= ?"
        params.append(date_to)
    query += " ORDER BY work_date DESC"
    cursor.execute(query, params)
    return [dict(ts) for ts in cursor.fetchall()]


@app.post("/timesheets", response_model=Timesheet, status_code=status.HTTP_201_CREATED)
def create_timesheet(timesheet: TimesheetCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] == "employee" and timesheet.employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only create timesheets for yourself")
    cursor.execute("SELECT timesheet_id FROM timesheets WHERE timesheet_id = ?", (timesheet.timesheet_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Timesheet ID already exists")
    cursor.execute("""
        INSERT INTO timesheets (timesheet_id, employee_id, project_id, work_date, hours_worked,
            task_description, billable, approved, submitted_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timesheet.timesheet_id, timesheet.employee_id, timesheet.project_id, timesheet.work_date,
        timesheet.hours_worked, timesheet.task_description, timesheet.billable,
        timesheet.approved, datetime.now().isoformat(), timesheet.notes
    ))
    db.commit()
    cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet.timesheet_id,))
    return dict(cursor.fetchone())


@app.put("/timesheets/{timesheet_id}", response_model=Timesheet)
def update_timesheet(timesheet_id: str, timesheet_update: TimesheetUpdate,
                     user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
    existing_ts = cursor.fetchone()
    if not existing_ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if user["role"] == "employee" and existing_ts["employee_id"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    update_fields, update_values = [], []
    for field, value in timesheet_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?")
        update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(timesheet_id)
    cursor.execute(f"UPDATE timesheets SET {', '.join(update_fields)} WHERE timesheet_id = ?", update_values)
    db.commit()
    cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
    return dict(cursor.fetchone())


@app.get("/timesheets/summary", response_model=TimesheetSummary)
def get_timesheet_summary(employee_id: Optional[str] = None, project_id: Optional[str] = None,
                          date_from: Optional[str] = None, date_to: Optional[str] = None,
                          user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = """
        SELECT SUM(hours_worked) as total_hours,
               SUM(CASE WHEN billable = 1 THEN hours_worked ELSE 0 END) as billable_hours,
               SUM(CASE WHEN billable = 0 THEN hours_worked ELSE 0 END) as non_billable_hours,
               SUM(CASE WHEN approved = 1 THEN hours_worked ELSE 0 END) as approved_hours,
               SUM(CASE WHEN approved = 0 THEN hours_worked ELSE 0 END) as pending_hours
        FROM timesheets WHERE 1=1
    """
    params = []
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if date_from:
        query += " AND work_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND work_date <= ?"
        params.append(date_to)
    cursor.execute(query, params)
    summary = cursor.fetchone()
    return {
        "total_hours":       summary["total_hours"] or 0,
        "billable_hours":    summary["billable_hours"] or 0,
        "non_billable_hours":summary["non_billable_hours"] or 0,
        "approved_hours":    summary["approved_hours"] or 0,
        "pending_hours":     summary["pending_hours"] or 0
    }


# ============================================================================
# DOCUMENTS
# ============================================================================
@app.get("/documents", response_model=List[Document])
def get_documents(project_id: Optional[str] = None, document_type: Optional[str] = None,
                  user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM documents WHERE 1=1"
    params = []
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and project_id:
        if project_id not in accessible_projects:
            raise HTTPException(status_code=403, detail="Access denied")
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if document_type:
        query += " AND document_type = ?"
        params.append(document_type)
    query += " ORDER BY upload_date DESC"
    cursor.execute(query, params)
    return [dict(d) for d in cursor.fetchall()]


@app.post("/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(document: DocumentCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT document_id FROM documents WHERE document_id = ?", (document.document_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Document ID already exists")
    cursor.execute("""
        INSERT INTO documents (document_id, document_name, document_type, file_path, file_size_kb,
            project_id, uploaded_by, upload_date, category, tags, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        document.document_id, document.document_name, document.document_type, document.file_path,
        document.file_size_kb, document.project_id, document.uploaded_by,
        datetime.now().isoformat(), document.category, document.tags, document.description
    ))
    log_action(cursor, user["employee_id"], "Create", "Document", document.document_id,
               f"Uploaded document: {document.document_name}")
    db.commit()
    cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document.document_id,))
    return dict(cursor.fetchone())


@app.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
    document = cursor.fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(document)


@app.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT document_id FROM documents WHERE document_id = ?", (document_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Document not found")
    cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
    log_action(cursor, user["employee_id"], "Delete", "Document", document_id, f"Deleted document {document_id}")
    db.commit()
    return None


# ============================================================================
# ACTIVITY LOGS
# ============================================================================
@app.get("/activity-logs", response_model=List[ActivityLog])
def get_activity_logs(user_id: Optional[str] = None, action_type: Optional[str] = None,
                      entity_type: Optional[str] = None, limit: int = 100,
                      user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] == "employee":
        raise HTTPException(status_code=403, detail="Access denied to activity logs")
    cursor = db.cursor()
    query = "SELECT * FROM activity_logs WHERE 1=1"
    params = []
    if user["role"] == "manager":
        supervised = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in supervised])
        query += f" AND user_id IN ({placeholders})"
        params.extend(supervised)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    if action_type:
        query += " AND action_type = ?"
        params.append(action_type)
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    return [dict(log) for log in cursor.fetchall()]


# ============================================================================
# NOTIFICATIONS
# ============================================================================
@app.get("/notifications", response_model=List[Notification])
def get_notifications(is_read: Optional[bool] = None, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params = [user["employee_id"]]
    if is_read is not None:
        query += " AND is_read = ?"
        params.append(is_read)
    query += " ORDER BY created_date DESC"
    cursor.execute(query, params)
    result = []
    for n in cursor.fetchall():
        notif = dict(n)
        notif["type"] = notif.get("type") or ""
        notif["title"] = notif.get("title") or ""
        notif["message"] = notif.get("message") or ""
        result.append(notif)
    return result


@app.get("/notifications/unread", response_model=List[Notification])
def get_unread_notifications(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_date DESC",
                   (user["employee_id"],))
    result = []
    for n in cursor.fetchall():
        notif = dict(n)
        notif["type"]         = notif.get("type") or ""
        notif["title"]        = notif.get("title") or ""
        notif["message"]      = notif.get("message") or ""
        notif["priority"]     = notif.get("priority") or "Normal"
        notif["is_read"]      = notif.get("is_read") or False
        notif["created_date"] = notif.get("created_date") or ""
        notif["read_date"]    = notif.get("read_date") or None
        notif["link"]         = notif.get("link") or None
        result.append(notif)
    return result


@app.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM notifications WHERE notification_id = ? AND user_id = ?",
                   (notification_id, user["employee_id"]))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Notification not found")
    cursor.execute("UPDATE notifications SET is_read = 1, read_date = ? WHERE notification_id = ?",
                   (datetime.now().isoformat(), notification_id))
    db.commit()
    return {"message": "Notification marked as read"}


@app.put("/notifications/mark-all-read")
def mark_all_notifications_read(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1, read_date = ? WHERE user_id = ? AND is_read = 0",
                   (datetime.now().isoformat(), user["employee_id"]))
    db.commit()
    return {"message": "All notifications marked as read"}


# ============================================================================
# STATISTICS — stats/tasks avec blocked inclus
# ============================================================================
@app.get("/stats/tasks")
def get_task_stats(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()
    if accessible_projects is None:
        cursor.execute("""
            SELECT COUNT(*) as total_tasks,
                   SUM(CASE WHEN status = 'Todo' THEN 1 ELSE 0 END) as todo,
                   SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
                   SUM(CASE WHEN status = 'Done' THEN 1 ELSE 0 END) as done,
                   SUM(CASE WHEN status = 'Blocked' THEN 1 ELSE 0 END) as blocked,
                   SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) as high_priority
            FROM tasks
        """)
    elif not accessible_projects:
        return {"total_tasks": 0, "todo": 0, "in_progress": 0, "done": 0, "blocked": 0, "critical": 0, "high_priority": 0}
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        cursor.execute(f"""
            SELECT COUNT(*) as total_tasks,
                   SUM(CASE WHEN status = 'Todo' THEN 1 ELSE 0 END) as todo,
                   SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
                   SUM(CASE WHEN status = 'Done' THEN 1 ELSE 0 END) as done,
                   SUM(CASE WHEN status = 'Blocked' THEN 1 ELSE 0 END) as blocked,
                   SUM(CASE WHEN priority = 'Critical' THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) as high_priority
            FROM tasks WHERE project_id IN ({placeholders})
        """, accessible_projects)
    return dict(cursor.fetchone())


@app.get("/stats/summary")
def get_summary_stats_dup(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    # alias — handled above
    return get_summary_stats(user=user, db=db)


@app.get("/stats/equipment")
def get_equipment_stats(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*) as total_equipment,
               SUM(CASE WHEN status = 'Available' THEN 1 ELSE 0 END) as available,
               SUM(CASE WHEN status = 'In Use' THEN 1 ELSE 0 END) as in_use,
               SUM(CASE WHEN status = 'Maintenance' THEN 1 ELSE 0 END) as maintenance,
               SUM(purchase_value) as total_value
        FROM equipment
    """)
    return dict(cursor.fetchone())


@app.get("/stats/issues")
def get_issue_stats(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()
    if accessible_projects is None:
        cursor.execute("""
            SELECT COUNT(*) as total_issues,
                   SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open,
                   SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN severity = 'Critical' THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN category = 'Safety' THEN 1 ELSE 0 END) as safety_issues
            FROM issues
        """)
    elif not accessible_projects:
        return {"total_issues": 0, "open": 0, "resolved": 0, "critical": 0, "safety_issues": 0}
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        cursor.execute(f"""
            SELECT COUNT(*) as total_issues,
                   SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open,
                   SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN severity = 'Critical' THEN 1 ELSE 0 END) as critical,
                   SUM(CASE WHEN category = 'Safety' THEN 1 ELSE 0 END) as safety_issues
            FROM issues WHERE project_id IN ({placeholders})
        """, accessible_projects)
    return dict(cursor.fetchone())


# ============================================================================
# REPORTS
# ============================================================================
def _group_by(items: list, key: str) -> dict:
    result = {}
    for item in items:
        val = item.get(key) or "Unknown"
        result[val] = result.get(val, 0) + 1
    return result


def generate_report_content(report_type, period_start, period_end, cursor, user=None):
    if report_type == "employee_performance":
        if user and user["role"] == "manager":
            supervised = user.get("supervised_employees") or []
            if not supervised:
                return {"total_employees": 0, "employees": []}
            placeholders = ",".join("?" * len(supervised))
            cursor.execute(f"""
                SELECT employee_id, first_name, last_name, position, role, department, assigned_projects
                FROM employees WHERE employee_id IN ({placeholders})
            """, supervised)
        else:
            cursor.execute("SELECT employee_id, first_name, last_name, position, role, department, assigned_projects FROM employees")
        employees = [dict(r) for r in cursor.fetchall()]
        for emp in employees:
            emp["project_count"] = len([p for p in (emp["assigned_projects"] or "").split(";") if p])
        return {
            "total_employees": len(employees),
            "by_role": _group_by(employees, "role"),
            "by_department": _group_by(employees, "department"),
            "employees": employees,
        }
    elif report_type == "budget":
        cursor.execute("""
            SELECT project_name, status, budget_eur, actual_cost_eur,
                   (actual_cost_eur - budget_eur) AS variance, completion_percentage
            FROM projects WHERE start_date <= ? AND end_date >= ?
        """, (period_end, period_start))
        rows = [dict(r) for r in cursor.fetchall()]
        total_budget = sum(r["budget_eur"] or 0 for r in rows)
        total_actual = sum(r["actual_cost_eur"] or 0 for r in rows)
        return {
            "total_budget": total_budget, "total_actual": total_actual,
            "total_variance": round(total_actual - total_budget, 2),
            "over_budget": [r for r in rows if (r["variance"] or 0) > 0],
            "under_budget": [r for r in rows if (r["variance"] or 0) <= 0],
            "breakdown": rows,
        }
    elif report_type == "task_completion":
        cursor.execute("SELECT task_id, title, status, priority, due_date, project_id, assigned_to FROM tasks")
        tasks = [dict(r) for r in cursor.fetchall()]
        total = len(tasks)
        done = len([t for t in tasks if t["status"] in ("Done", "Completed")])
        today = datetime.now().isoformat()
        return {
            "total_tasks": total, "completed": done,
            "completion_rate": round(done / total * 100, 1) if total else 0,
            "by_status": _group_by(tasks, "status"),
            "by_priority": _group_by(tasks, "priority"),
            "overdue": [t for t in tasks if t["due_date"] and t["due_date"] < today and t["status"] not in ("Done", "Completed")],
            "tasks": tasks,
        }
    elif report_type == "custom":
        cursor.execute("SELECT * FROM projects")
        projects = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM employees")
        employees = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT * FROM tasks")
        tasks = [dict(r) for r in cursor.fetchall()]
        return {"projects": projects, "employees": employees, "tasks": tasks}
    return {}


@app.post("/reports/generate", response_model=Report, status_code=status.HTTP_201_CREATED)
def generate_report(report: ReportCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    if user["role"] == "manager" and report.report_type == "custom":
        raise HTTPException(status_code=403, detail="Les managers ne peuvent pas générer un rapport personnalisé complet")
    cursor = db.cursor()
    cursor.execute("SELECT report_id FROM reports WHERE report_id = ?", (report.report_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Report ID already exists")
    content = generate_report_content(report.report_type, report.period_start, report.period_end, cursor, user)
    cursor.execute("""
        INSERT INTO reports (report_id, report_type, title, period_start, period_end, generated_by,
            generation_date, filters, parameters, status, content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Completed', ?)
    """, (
        report.report_id, report.report_type, report.title, report.period_start,
        report.period_end, report.generated_by, datetime.now().isoformat(),
        report.filters, report.parameters, json.dumps(content)
    ))
    log_action(cursor, user["employee_id"], "Create", "Report", report.report_id,
               f"Generated {report.report_type} report: {report.title}")
    db.commit()
    cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report.report_id,))
    return dict(cursor.fetchone())


@app.get("/reports")
def get_reports(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    base_query = """
        SELECT r.*, e.first_name || ' ' || e.last_name AS generated_by_name
        FROM reports r LEFT JOIN employees e ON r.generated_by = e.employee_id
    """
    if user["role"] == "ceo":
        cursor.execute(base_query + " ORDER BY r.generation_date DESC")
    elif user["role"] == "manager":
        cursor.execute(base_query + " WHERE r.generated_by = ? ORDER BY r.generation_date DESC",
                       (user["employee_id"],))
    else:
        raise HTTPException(status_code=403, detail="Accès aux rapports refusé")
    return [dict(r) for r in cursor.fetchall()]


@app.get("/reports/{report_id}/download")
def download_report_pdf(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    from fastapi.responses import FileResponse
    cursor = db.cursor()
    if user["role"] == "ceo":
        cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
    elif user["role"] == "manager":
        cursor.execute("SELECT * FROM reports WHERE report_id = ? AND generated_by = ?",
                       (report_id, user["employee_id"]))
    else:
        raise HTTPException(status_code=403, detail="Accès refusé")
    report = cursor.fetchone()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report = dict(report)
    content = json.loads(report.get("content") or "{}")
    pdf_dir = "reports_pdf"
    os.makedirs(pdf_dir, exist_ok=True)
    file_path = os.path.join(pdf_dir, f"{report_id}.pdf")
    success = generate_pdf(content, file_path, report["title"])
    if not success:
        raise HTTPException(status_code=500, detail="PDF generation failed")
    cursor.execute("UPDATE reports SET file_path = ? WHERE report_id = ?", (file_path, report_id))
    db.commit()
    return FileResponse(path=file_path, filename=f"{report['title'].replace(' ', '_')}.pdf", media_type="application/pdf")


@app.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    if user["role"] == "ceo":
        cursor.execute("SELECT report_id FROM reports WHERE report_id = ?", (report_id,))
    else:
        cursor.execute("SELECT report_id FROM reports WHERE report_id = ? AND generated_by = ?",
                       (report_id, user["employee_id"]))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Report not found or access denied")
    cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
    log_action(cursor, user["employee_id"], "Delete", "Report", report_id, f"Deleted report {report_id}")
    db.commit()
    return None


def generate_pdf(report_data: dict, file_path: str, title: str):
    try:
        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 60, title)
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 80, f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y = height - 120
        c.setFont("Helvetica", 11)

        def write_line(text, indent=0):
            nonlocal y
            if y < 60:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 11)
            c.drawString(50 + indent, y, str(text)[:100])
            y -= 18

        def render_value(key, value, indent=0):
            if isinstance(value, dict):
                write_line(f"{key}:", indent)
                for k, v in value.items():
                    render_value(k, v, indent + 20)
            elif isinstance(value, list):
                write_line(f"{key}: ({len(value)} items)", indent)
                for i, item in enumerate(value[:20]):
                    if isinstance(item, dict):
                        name = item.get("project_name") or item.get("first_name") or item.get("title") or f"Item {i+1}"
                        write_line(f"  • {name}", indent + 10)
                    else:
                        write_line(f"  • {item}", indent + 10)
                if len(value) > 20:
                    write_line(f"  ... and {len(value) - 20} more", indent + 10)
            else:
                write_line(f"{key}: {value}", indent)

        for key, value in report_data.items():
            render_value(key, value)
        c.save()
        return True
    except Exception as e:
        print(f"PDF generation error: {e}")
        return False


# ============================================================================
# AUTH EXTRAS
# ============================================================================
@app.patch("/employees/{employee_id}/change-password")
def change_password(employee_id: str, body: dict,
                    user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["employee_id"] != employee_id:
        raise HTTPException(status_code=403, detail="You can only change your own password")
    if not body.get("new_password"):
        raise HTTPException(status_code=400, detail="new_password is required")
    if len(body["new_password"]) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    new_hash = argon2.hash(body["new_password"])
    cursor = db.cursor()
    cursor.execute("UPDATE employees SET password_hash = ?, must_change_password = 0 WHERE employee_id = ?",
                   (new_hash, employee_id))
    log_action(cursor, user["employee_id"], "Update", "Employee", employee_id, "Password changed")
    db.commit()
    return {"message": "Password changed successfully"}


@app.post("/refresh-token")
def refresh_token(user: dict = Depends(authenticate_with_token)):
    token_data = {"sub": user["username"], "employee_id": user["employee_id"], "role": user["role"]}
    new_token = create_access_token(token_data)
    return {"access_token": new_token, "token_type": "bearer"}


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM employees WHERE username = ?", (credentials.username,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
                            headers={"WWW-Authenticate": "Basic"})
    user_data = dict(row)
    if user_data.get("password_hash"):
        try:
            if not argon2.verify(credentials.password, user_data["password_hash"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
                                    headers={"WWW-Authenticate": "Basic"})
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials",
                                headers={"WWW-Authenticate": "Basic"})
    return build_user_dict(user_data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)