from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from passlib.hash import argon2
from core.database import get_db
from core.auth import authenticate_with_token, log_action, EMPLOYEE_LOCKED_FIELDS
from core.models import Employee, EmployeeCreate, EmployeeUpdate, LeaveStats

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("", response_model=List[Employee])
def get_employees(
    department: Optional[str] = None,
    role: Optional[str] = None,
    employee_id: Optional[str] = None,
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


@router.get("/{employee_id}", response_model=Employee)
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


@router.post("", response_model=Employee, status_code=status.HTTP_201_CREATED)
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


@router.put("/{employee_id}", response_model=Employee)
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
    log_action(cursor, user["employee_id"], "Update", "Employee", employee_id, f"Updated employee {employee_id}")
    db.commit()
    cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    return dict(cursor.fetchone())


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.patch("/{employee_id}/change-password")
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


@router.get("/{employee_id}/leave-stats", response_model=LeaveStats)
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