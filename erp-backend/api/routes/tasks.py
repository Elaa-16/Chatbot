from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, date
from core.database import get_db
from core.auth import authenticate_with_token, check_edit_permission, get_accessible_projects, log_action
from core.models import Task, TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=List[Task])
def get_tasks(
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    overdue: Optional[bool] = None,
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


@router.get("/{task_id}", response_model=Task)
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


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
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


@router.put("/{task_id}", response_model=Task)
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


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.put("/{task_id}/status")
def update_task_status(task_id: str, new_status: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
    log_action(cursor, user["employee_id"], "Update", "Task", task_id, f"Status changed to {new_status}")
    db.commit()
    return {"message": "Status updated", "task_id": task_id, "new_status": new_status}