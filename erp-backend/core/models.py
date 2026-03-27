from pydantic import BaseModel
from typing import List, Optional


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class User(BaseModel):
    employee_id: str
    username: str
    role: str
    assigned_projects: List[str]
    supervised_employees: List[str]


# ── Projects ──────────────────────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    project_id: str
    project_name: str
    project_type: Optional[str] = None
    client_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = "Planning"
    budget: Optional[float] = None
    actual_cost: Optional[float] = 0
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
    budget: Optional[float] = None
    actual_cost: Optional[float] = None
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
    budget: Optional[float]
    actual_cost: Optional[float]
    completion_percentage: Optional[int]
    location: Optional[str]
    description: Optional[str]


# ── Employees ─────────────────────────────────────────────────────────────────
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
    salary: Optional[float] = None
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
    salary: Optional[float] = None
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


# ── KPIs ──────────────────────────────────────────────────────────────────────
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
    quality_score: float
    safety_incidents: Optional[int]
    client_satisfaction_score: Optional[float]
    cost_performance_index: Optional[float]
    schedule_performance_index: Optional[float]
    risk_level: Optional[str]
    team_productivity_percentage: float



# ── Leave Requests ────────────────────────────────────────────────────────────
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


# ── Tasks ─────────────────────────────────────────────────────────────────────
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


# ── Issues ────────────────────────────────────────────────────────────────────
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

class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_date: Optional[str] = None

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


# ── Equipment ─────────────────────────────────────────────────────────────────
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


# ── Suppliers ─────────────────────────────────────────────────────────────────
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


# ── Purchase Orders ───────────────────────────────────────────────────────────
class PurchaseOrderCreate(BaseModel):
    po_id: str
    supplier_id: str
    project_id: str
    order_date: str
    delivery_date: Optional[str] = None
    items_description: str
    total_amount: float
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
    total_amount: float
    status: str
    created_by: str
    created_date: str
    approved_by: Optional[str]
    approval_date: Optional[str]
    notes: Optional[str]


# ── Timesheets ────────────────────────────────────────────────────────────────
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


# ── Documents ─────────────────────────────────────────────────────────────────
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


# ── Notifications ─────────────────────────────────────────────────────────────
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


# ── Activity Logs ─────────────────────────────────────────────────────────────
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


# ── Reports ───────────────────────────────────────────────────────────────────
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
    
class ReportCreate(BaseModel):
    report_type: str
    title: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    filters: Optional[str] = "{}"
    parameters: Optional[str] = "{}"

# ── API Whitelist ─────────────────────────────────────────────────────────────
class ApiWhitelistCreate(BaseModel):
    endpoint: str
    methods: str
    description: Optional[str] = None
    is_active: Optional[int] = 1

class ApiWhitelistUpdate(BaseModel):
    endpoint: Optional[str] = None
    methods: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[int] = None

class ApiWhitelist(BaseModel):
    id: int
    endpoint: str
    methods: str
    description: Optional[str]
    is_active: int