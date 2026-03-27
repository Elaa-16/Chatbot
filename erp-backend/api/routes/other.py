"""
Remaining routes: Issues, Equipment, Suppliers, Purchase Orders,
Timesheets, Notifications, Documents, Activity Logs, Stats
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from core.database import get_db
from core.auth import authenticate_with_token, check_edit_permission, get_accessible_projects, log_action
from core.models import (
    Issue, IssueCreate, IssueUpdate,
    Equipment, EquipmentCreate, EquipmentUpdate, ReportCreate,
    Supplier, SupplierCreate, SupplierUpdate,
    PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate,
    Timesheet, TimesheetCreate, TimesheetUpdate, TimesheetSummary,
    Notification, Document, DocumentCreate,
    ActivityLog,
)

# ── Issues ────────────────────────────────────────────────────────────────────
issues_router = APIRouter(prefix="/issues", tags=["Issues"])

@issues_router.get("", response_model=List[Issue])
def get_issues(project_id: Optional[str] = None, severity: Optional[str] = None,
               status: Optional[str] = None, category: Optional[str] = None,
               unresolved: Optional[bool] = None,
               user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
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
        query += " AND project_id = ?"; params.append(project_id)
    if severity:
        query += " AND severity = ?"; params.append(severity)
    if status:
        query += " AND status = ?"; params.append(status)
    if category:
        query += " AND category = ?"; params.append(category)
    if unresolved is True:
        query += " AND status IN ('Open', 'In Progress')"
    query += " ORDER BY created_date DESC, severity DESC"
    cursor.execute(query, params)
    return [dict(i) for i in cursor.fetchall()]

@issues_router.post("", response_model=Issue, status_code=status.HTTP_201_CREATED)
def create_issue(issue: IssueCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT issue_id FROM issues WHERE issue_id = ?", (issue.issue_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Issue ID already exists")
    cursor.execute("""
        INSERT INTO issues (issue_id, project_id, reported_by, title, description, severity,
            category, status, assigned_to, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (issue.issue_id, issue.project_id, issue.reported_by, issue.title, issue.description,
          issue.severity, issue.category, issue.status, issue.assigned_to, datetime.now().isoformat()))
    cursor.execute("SELECT employee_id FROM employees WHERE role = 'ceo' LIMIT 1")
    ceo = cursor.fetchone()
    if ceo:
        notif_id = f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        priority = 'High' if issue.severity in ('Critical', 'High') else 'Normal'
        icon = '🚨' if issue.severity == 'Critical' else '⚠️'
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, type, title, message, link, is_read, priority, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (notif_id, ceo["employee_id"], 'Issue', f"{icon} Nouvel Incident {issue.severity}",
              f"{issue.title} — Projet: {issue.project_id} — Catégorie: {issue.category}",
              '/issues', 0, priority, datetime.now().isoformat()))
    log_action(cursor, user["employee_id"], "Create", "Issue", issue.issue_id,
               f"Reported issue: {issue.title} (severity: {issue.severity})")
    db.commit()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue.issue_id,))
    return dict(cursor.fetchone())

@issues_router.put("/{issue_id}", response_model=Issue)
def update_issue(issue_id: str, issue_update: IssueUpdate,
                 user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Issue not found")
    update_fields, update_values = [], []
    for field, value in issue_update.model_dump(exclude_unset=True).items():
        if field == "location": continue
        update_fields.append(f"{field} = ?"); update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(issue_id)
    cursor.execute(f"UPDATE issues SET {', '.join(update_fields)} WHERE issue_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Issue", issue_id, f"Updated issue {issue_id}")
    db.commit()
    cursor.execute("SELECT * FROM issues WHERE issue_id = ?", (issue_id,))
    return dict(cursor.fetchone())

@issues_router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── Equipment ─────────────────────────────────────────────────────────────────
equipment_router = APIRouter(prefix="/equipment", tags=["Equipment"])

@equipment_router.get("", response_model=List[Equipment])
def get_equipment(status: Optional[str] = None, category: Optional[str] = None,
                  current_project_id: Optional[str] = None,
                  user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM equipment WHERE 1=1"
    params = []
    if status: query += " AND status = ?"; params.append(status)
    if category: query += " AND category = ?"; params.append(category)
    if current_project_id: query += " AND current_project_id = ?"; params.append(current_project_id)
    query += " ORDER BY name ASC"
    cursor.execute(query, params)
    return [dict(eq) for eq in cursor.fetchall()]

@equipment_router.get("/available", response_model=List[Equipment])
def get_available_equipment(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment WHERE status = 'Available' ORDER BY name ASC")
    return [dict(eq) for eq in cursor.fetchall()]

@equipment_router.post("", response_model=Equipment, status_code=status.HTTP_201_CREATED)
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
    """, (equipment.equipment_id, equipment.name, equipment.category, equipment.serial_number,
          equipment.status, equipment.current_project_id, equipment.assigned_to, equipment.location,
          equipment.purchase_date, equipment.purchase_value, equipment.last_maintenance,
          equipment.next_maintenance, equipment.notes))
    log_action(cursor, user["employee_id"], "Create", "Equipment", equipment.equipment_id,
               f"Added equipment: {equipment.name}")
    db.commit()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment.equipment_id,))
    return dict(cursor.fetchone())

@equipment_router.put("/{equipment_id}", response_model=Equipment)
def update_equipment(equipment_id: str, equipment_update: EquipmentUpdate,
                     user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Equipment not found")
    update_fields, update_values = [], []
    for field, value in equipment_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?"); update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(equipment_id)
    cursor.execute(f"UPDATE equipment SET {', '.join(update_fields)} WHERE equipment_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Equipment", equipment_id, f"Updated equipment {equipment_id}")
    db.commit()
    cursor.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,))
    return dict(cursor.fetchone())

@equipment_router.put("/{equipment_id}/assign")
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

@equipment_router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── Suppliers ─────────────────────────────────────────────────────────────────
suppliers_router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@suppliers_router.get("", response_model=List[Supplier])
def get_suppliers(category: Optional[str] = None, status: Optional[str] = None,
                  search: Optional[str] = None, sort_by_rating: Optional[bool] = None,
                  user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM suppliers WHERE 1=1"
    params = []
    if category: query += " AND category = ?"; params.append(category)
    if status: query += " AND status = ?"; params.append(status)
    if search:
        query += " AND (supplier_name LIKE ? OR contact_person LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY rating DESC" if sort_by_rating else " ORDER BY supplier_name ASC"
    cursor.execute(query, params)
    return [dict(s) for s in cursor.fetchall()]

@suppliers_router.post("", response_model=Supplier, status_code=status.HTTP_201_CREATED)
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
    """, (supplier.supplier_id, supplier.supplier_name, supplier.contact_person, supplier.email,
          supplier.phone, supplier.address, supplier.city, supplier.country, supplier.category,
          supplier.rating, supplier.status, datetime.now().isoformat(), supplier.notes))
    log_action(cursor, user["employee_id"], "Create", "Supplier", supplier.supplier_id,
               f"Created supplier: {supplier.supplier_name}")
    db.commit()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier.supplier_id,))
    return dict(cursor.fetchone())

@suppliers_router.put("/{supplier_id}", response_model=Supplier)
def update_supplier(supplier_id: str, supplier_update: SupplierUpdate,
                    user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Supplier not found")
    update_fields, update_values = [], []
    for field, value in supplier_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?"); update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(supplier_id)
    cursor.execute(f"UPDATE suppliers SET {', '.join(update_fields)} WHERE supplier_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "Supplier", supplier_id, f"Updated supplier {supplier_id}")
    db.commit()
    cursor.execute("SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,))
    return dict(cursor.fetchone())

@suppliers_router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── Purchase Orders ───────────────────────────────────────────────────────────
po_router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])

@po_router.get("", response_model=List[PurchaseOrder])
def get_purchase_orders(project_id: Optional[str] = None, supplier_id: Optional[str] = None,
                        status: Optional[str] = None,
                        user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM purchase_orders WHERE 1=1"
    params = []
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None:
        if not accessible_projects: return []
        placeholders = ','.join(['?' for _ in accessible_projects])
        query += f" AND project_id IN ({placeholders})"
        params.extend(accessible_projects)
    if project_id: query += " AND project_id = ?"; params.append(project_id)
    if supplier_id: query += " AND supplier_id = ?"; params.append(supplier_id)
    if status: query += " AND status = ?"; params.append(status)
    query += " ORDER BY order_date DESC"
    cursor.execute(query, params)
    return [dict(o) for o in cursor.fetchall()]

@po_router.post("", response_model=PurchaseOrder, status_code=status.HTTP_201_CREATED)
def create_purchase_order(po: PurchaseOrderCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT po_id FROM purchase_orders WHERE po_id = ?", (po.po_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Purchase order ID already exists")
    cursor.execute("""
        INSERT INTO purchase_orders (po_id, supplier_id, project_id, order_date, delivery_date,
            items_description, total_amount, status, created_by, created_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (po.po_id, po.supplier_id, po.project_id, po.order_date, po.delivery_date,
          po.items_description, po.total_amount, po.status, po.created_by,
          datetime.now().isoformat(), po.notes))
    log_action(cursor, user["employee_id"], "Create", "PurchaseOrder", po.po_id,
               f"Created PO {po.po_id} for project {po.project_id}")
    db.commit()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po.po_id,))
    return dict(cursor.fetchone())

@po_router.put("/{po_id}", response_model=PurchaseOrder)
def update_purchase_order(po_id: str, po_update: PurchaseOrderUpdate,
                          user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    check_edit_permission(user)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Purchase order not found")
    update_fields, update_values = [], []
    for field, value in po_update.model_dump(exclude_unset=True).items():
        update_fields.append(f"{field} = ?"); update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(po_id)
    cursor.execute(f"UPDATE purchase_orders SET {', '.join(update_fields)} WHERE po_id = ?", update_values)
    log_action(cursor, user["employee_id"], "Update", "PurchaseOrder", po_id, f"Updated PO {po_id}")
    db.commit()
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    return dict(cursor.fetchone())

@po_router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── Timesheets ────────────────────────────────────────────────────────────────
timesheets_router = APIRouter(prefix="/timesheets", tags=["Timesheets"])

@timesheets_router.get("", response_model=List[Timesheet])
def get_timesheets(employee_id: Optional[str] = None, project_id: Optional[str] = None,
                   approved: Optional[bool] = None, date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM timesheets WHERE 1=1"
    params = []
    if user["role"] == "employee":
        query += " AND employee_id = ?"; params.append(user["employee_id"])
    elif user["role"] == "manager":
        supervised = user["supervised_employees"] + [user["employee_id"]]
        placeholders = ','.join(['?' for _ in supervised])
        query += f" AND employee_id IN ({placeholders})"; params.extend(supervised)
    if employee_id: query += " AND employee_id = ?"; params.append(employee_id)
    if project_id: query += " AND project_id = ?"; params.append(project_id)
    if approved is not None: query += " AND approved = ?"; params.append(approved)
    if date_from: query += " AND date >= ?"; params.append(date_from)
    if date_to: query += " AND date <= ?"; params.append(date_to)
    query += " ORDER BY date DESC"
    cursor.execute(query, params)
    return [dict(ts) for ts in cursor.fetchall()]

@timesheets_router.get("/summary", response_model=TimesheetSummary)
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
    if employee_id: query += " AND employee_id = ?"; params.append(employee_id)
    if project_id: query += " AND project_id = ?"; params.append(project_id)
    if date_from: query += " AND date >= ?"; params.append(date_from)
    if date_to: query += " AND date <= ?"; params.append(date_to)
    cursor.execute(query, params)
    s = cursor.fetchone()
    return {"total_hours": s["total_hours"] or 0, "billable_hours": s["billable_hours"] or 0,
            "non_billable_hours": s["non_billable_hours"] or 0, "approved_hours": s["approved_hours"] or 0,
            "pending_hours": s["pending_hours"] or 0}

@timesheets_router.post("", response_model=Timesheet, status_code=status.HTTP_201_CREATED)
def create_timesheet(timesheet: TimesheetCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] == "employee" and timesheet.employee_id != user["employee_id"]:
        raise HTTPException(status_code=403, detail="You can only create timesheets for yourself")
    cursor.execute("SELECT timesheet_id FROM timesheets WHERE timesheet_id = ?", (timesheet.timesheet_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Timesheet ID already exists")
    cursor.execute("""
        INSERT INTO timesheets (timesheet_id, employee_id, project_id, date, hours_worked,
            task_description, billable, approved, submitted_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timesheet.timesheet_id, timesheet.employee_id, timesheet.project_id, timesheet.date,
          timesheet.hours_worked, timesheet.task_description, timesheet.billable,
          timesheet.approved, datetime.now().isoformat(), timesheet.notes))
    db.commit()
    cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet.timesheet_id,))
    return dict(cursor.fetchone())

@timesheets_router.put("/{timesheet_id}", response_model=Timesheet)
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
        update_fields.append(f"{field} = ?"); update_values.append(value)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_values.append(timesheet_id)
    cursor.execute(f"UPDATE timesheets SET {', '.join(update_fields)} WHERE timesheet_id = ?", update_values)
    db.commit()
    cursor.execute("SELECT * FROM timesheets WHERE timesheet_id = ?", (timesheet_id,))
    return dict(cursor.fetchone())


# ── Notifications ─────────────────────────────────────────────────────────────
notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])

@notifications_router.get("", response_model=List[Notification])
def get_notifications(is_read: Optional[bool] = None, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params = [user["employee_id"]]
    if is_read is not None:
        query += " AND is_read = ?"; params.append(is_read)
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

@notifications_router.get("/unread", response_model=List[Notification])
def get_unread_notifications(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_date DESC",
                   (user["employee_id"],))
    result = []
    for n in cursor.fetchall():
        notif = dict(n)
        notif["type"] = notif.get("type") or ""
        notif["title"] = notif.get("title") or ""
        notif["message"] = notif.get("message") or ""
        notif["priority"] = notif.get("priority") or "Normal"
        notif["is_read"] = notif.get("is_read") or False
        notif["created_date"] = notif.get("created_date") or ""
        notif["read_date"] = notif.get("read_date") or None
        notif["link"] = notif.get("link") or None
        result.append(notif)
    return result

@notifications_router.put("/{notification_id}/read")
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

@notifications_router.put("/mark-all-read")
def mark_all_notifications_read(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1, read_date = ? WHERE user_id = ? AND is_read = 0",
                   (datetime.now().isoformat(), user["employee_id"]))
    db.commit()
    return {"message": "All notifications marked as read"}


# ── Documents ─────────────────────────────────────────────────────────────────
documents_router = APIRouter(prefix="/documents", tags=["Documents"])

@documents_router.get("", response_model=List[Document])
def get_documents(project_id: Optional[str] = None, document_type: Optional[str] = None,
                  user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM documents WHERE 1=1"
    params = []
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and project_id:
        if project_id not in accessible_projects:
            raise HTTPException(status_code=403, detail="Access denied")
    if project_id: query += " AND project_id = ?"; params.append(project_id)
    if document_type: query += " AND document_type = ?"; params.append(document_type)
    query += " ORDER BY upload_date DESC"
    cursor.execute(query, params)
    return [dict(d) for d in cursor.fetchall()]

@documents_router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
def create_document(document: DocumentCreate, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT document_id FROM documents WHERE document_id = ?", (document.document_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Document ID already exists")
    cursor.execute("""
        INSERT INTO documents (document_id, document_name, document_type, file_path, file_size_kb,
            project_id, uploaded_by, upload_date, category, tags, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (document.document_id, document.document_name, document.document_type, document.file_path,
          document.file_size_kb, document.project_id, document.uploaded_by,
          datetime.now().isoformat(), document.category, document.tags, document.description))
    log_action(cursor, user["employee_id"], "Create", "Document", document.document_id,
               f"Uploaded document: {document.document_name}")
    db.commit()
    cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document.document_id,))
    return dict(cursor.fetchone())

@documents_router.get("/{document_id}", response_model=Document)
def get_document(document_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
    document = cursor.fetchone()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(document)

@documents_router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
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


# ── Activity Logs ─────────────────────────────────────────────────────────────
logs_router = APIRouter(prefix="/activity-logs", tags=["Logs"])

@logs_router.get("", response_model=List[ActivityLog])
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
        query += f" AND user_id IN ({placeholders})"; params.extend(supervised)
    if user_id: query += " AND user_id = ?"; params.append(user_id)
    if action_type: query += " AND action_type = ?"; params.append(action_type)
    if entity_type: query += " AND entity_type = ?"; params.append(entity_type)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    return [dict(log) for log in cursor.fetchall()]


# ── Stats ─────────────────────────────────────────────────────────────────────
stats_router = APIRouter(prefix="/stats", tags=["Statistics"])

@stats_router.get("/summary")
def get_summary_stats(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    cursor = db.cursor()
    if accessible_projects is None:
        cursor.execute("""
            SELECT COUNT(*) as total_projects, SUM(budget) as total_budget,
                   SUM(actual_cost) as total_actual_cost, AVG(completion_percentage) as avg_completion
            FROM projects
        """)
    elif not accessible_projects:
        return {"total_projects": 0, "total_budget": 0, "total_actual_cost": 0, "avg_completion": 0}
    else:
        placeholders = ','.join(['?' for _ in accessible_projects])
        cursor.execute(f"""
            SELECT COUNT(*) as total_projects, SUM(budget) as total_budget,
                   SUM(actual_cost) as total_actual_cost, AVG(completion_percentage) as avg_completion
            FROM projects WHERE project_id IN ({placeholders})
        """, accessible_projects)
    return dict(cursor.fetchone())

@stats_router.get("/tasks")
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

@stats_router.get("/equipment")
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

@stats_router.get("/issues")
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


# ── Reports ───────────────────────────────────────────────────────────────────
reports_router = APIRouter(prefix="/reports", tags=["Reports"])

@reports_router.get("")
def get_reports(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    if user["role"] == "ceo":
        cursor.execute("""
            SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
            FROM reports r
            LEFT JOIN employees e ON r.generated_by = e.employee_id
            ORDER BY r.generation_date DESC
        """)
    elif user["role"] == "manager":
        cursor.execute("""
            SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
            FROM reports r
            LEFT JOIN employees e ON r.generated_by = e.employee_id
            WHERE r.generated_by = ?
            ORDER BY r.generation_date DESC
        """, (user["employee_id"],))
    else:
        raise HTTPException(status_code=403, detail="Accès aux rapports refusé")
    return [dict(r) for r in cursor.fetchall()]


@reports_router.get("/{report_id}")
def get_report(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Accès aux rapports refusé")
    cursor = db.cursor()
    cursor.execute("""
        SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
        FROM reports r
        LEFT JOIN employees e ON r.generated_by = e.employee_id
        WHERE r.report_id = ?
    """, (report_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if user["role"] == "manager" and dict(row)["generated_by"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return dict(row)


@reports_router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_report(
        report: ReportCreate,
        user: dict = Depends(authenticate_with_token),
        db=Depends(get_db)
):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Accès aux rapports refusé")

    cursor = db.cursor()
    report_id = f"RPT{datetime.now().strftime('%Y%m%d%H%M%S')}"
    report_title = report.title or f"Rapport {report.report_type} — {datetime.now().strftime('%Y-%m-%d')}"

    cursor.execute("""
        INSERT INTO reports (report_id, report_type, title, period_start, period_end,
            generated_by, generation_date, file_path, filters, parameters, status, content)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id, report.report_type, report_title,
        report.period_start, report.period_end,
        user["employee_id"], datetime.now().isoformat(),
        None, report.filters or "{}", report.parameters or "{}",
        "Completed", ""
    ))

    log_action(cursor, user["employee_id"], "Create", "Report", report_id,
               f"Generated report: {report_title}")
    db.commit()

    cursor.execute("""
        SELECT r.*, e.first_name || ' ' || e.last_name as generated_by_name
        FROM reports r
        LEFT JOIN employees e ON r.generated_by = e.employee_id
        WHERE r.report_id = ?
    """, (report_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"report_id": report_id, "status": "Completed"}


@reports_router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    if user["role"] not in ("ceo", "manager"):
        raise HTTPException(status_code=403, detail="Accès aux rapports refusé")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    if user["role"] == "manager" and dict(row)["generated_by"] != user["employee_id"]:
        raise HTTPException(status_code=403, detail="Accès refusé — vous ne pouvez supprimer que vos propres rapports")
    cursor.execute("DELETE FROM reports WHERE report_id = ?", (report_id,))
    log_action(cursor, user["employee_id"], "Delete", "Report", report_id, f"Deleted report {report_id}")
    db.commit()
    return None