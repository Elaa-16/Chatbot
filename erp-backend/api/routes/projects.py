from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from core.database import get_db
from core.auth import authenticate_with_token, check_edit_permission, get_accessible_projects, sync_project_assignments, log_action
from core.models import Project, ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[Project])
def get_projects(
    status: Optional[str] = None,
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


@router.get("/{project_id}", response_model=Project)
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


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
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


@router.put("/{project_id}", response_model=Project)
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
    log_action(cursor, user["employee_id"], "Update", "Project", project_id, f"Updated project: {project_id}")
    db.commit()
    cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
    return dict(cursor.fetchone())


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
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