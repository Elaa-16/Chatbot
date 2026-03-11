from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from core.database import get_db
from core.auth import authenticate_with_token, log_action
from core.models import LeaveRequest, LeaveRequestCreate

router = APIRouter(prefix="/leave-requests", tags=["Leave Requests"])


@router.get("", response_model=List[LeaveRequest])
def get_leave_requests(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    leave_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year: Optional[int] = None,
    user: dict = Depends(authenticate_with_token),
    db=Depends(get_db)
):
    cursor = db.cursor()
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
    if status:
        query += " AND status = ?"
        params.append(status)
    if employee_id:
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


@router.get("/pending", response_model=List[LeaveRequest])
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


@router.get("/{request_id}", response_model=LeaveRequest)
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


@router.post("", response_model=LeaveRequest, status_code=status.HTTP_201_CREATED)
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

    # ── INSERT leave request FIRST ────────────────────────────────────────────
    cursor.execute("""
        INSERT INTO leave_requests (request_id, employee_id, employee_name, leave_type, start_date, end_date,
            total_days, reason, status, requested_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (
        leave_request.request_id, leave_request.employee_id, leave_request.employee_name,
        leave_request.leave_type, leave_request.start_date, leave_request.end_date,
        leave_request.total_days, leave_request.reason, datetime.now().isoformat()
    ))

    # ── Notify approver ───────────────────────────────────────────────────────
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

    notif_message = (
        f"{leave_request.employee_name} a demandé {leave_request.total_days} jour(s) "
        f"({leave_request.leave_type}) du {leave_request.start_date} au {leave_request.end_date}"
    )

    if approver_id:
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, type, title, message,
                priority, is_read, created_date, related_entity_type, related_entity_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            approver_id, 'Leave', '📋 Nouvelle demande de congé',
            notif_message, 'High', 0, datetime.now().isoformat(),
            'leave_request', leave_request.request_id
        ))

    # ── Always notify RH ──────────────────────────────────────────────────────
    cursor.execute("SELECT employee_id FROM employees WHERE role = 'rh' LIMIT 1")
    rh = cursor.fetchone()
    if rh and rh["employee_id"] != approver_id:
        cursor.execute("""
            INSERT INTO notifications (notification_id, user_id, type, title, message,
                priority, is_read, created_date, related_entity_type, related_entity_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"NOT{datetime.now().strftime('%Y%m%d%H%M%S%f')}R",
            rh["employee_id"], 'Leave', '📋 Nouvelle demande de congé',
            notif_message, 'High', 0, datetime.now().isoformat(),
            'leave_request', leave_request.request_id
        ))

    log_action(cursor, user["employee_id"], "Create", "LeaveRequest", leave_request.request_id,
               f"Submitted leave request: {leave_request.leave_type} {leave_request.total_days}j")
    db.commit()

    cursor.execute("SELECT * FROM leave_requests WHERE request_id = ?", (leave_request.request_id,))
    return dict(cursor.fetchone())

@router.put("/{request_id}/approve", response_model=LeaveRequest)
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


@router.put("/{request_id}/reject", response_model=LeaveRequest)
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


@router.put("/{request_id}/cancel", response_model=LeaveRequest)
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