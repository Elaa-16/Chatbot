from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from core.database import get_db
from core.auth import authenticate_with_token, check_edit_permission, get_accessible_projects, log_action
from core.models import KPI, KPICreate, KPIUpdate

router = APIRouter(prefix="/kpis", tags=["KPIs"])


@router.get("", response_model=List[KPI])
def get_kpis(
    delayed: Optional[bool] = None,
    over_budget: Optional[bool] = None,
    risk_level: Optional[str] = None,
    project_id: Optional[str] = None,
    spi_max: Optional[float] = None,
    cpi_max: Optional[float] = None,
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


@router.get("/project/{project_id}", response_model=List[KPI])
def get_project_kpis(project_id: str, user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    accessible_projects = get_accessible_projects(user, db)
    if accessible_projects is not None and project_id not in accessible_projects:
        raise HTTPException(status_code=403, detail=f"Access denied to KPIs for project {project_id}")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM kpis WHERE project_id = ? ORDER BY kpi_date DESC", (project_id,))
    return [dict(k) for k in cursor.fetchall()]


@router.get("/{kpi_id}", response_model=KPI)
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


@router.post("", response_model=KPI, status_code=status.HTTP_201_CREATED)
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
        INSERT INTO kpis (kpi_id, project_id, project_name, kpi_date, budget_variance_percentage,
            schedule_variance_days, quality_score, safety_incidents, client_satisfaction_score,
            team_productivity_percentage, cost_performance_index, schedule_performance_index, risk_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kpi.kpi_id, kpi.project_id, kpi.project_name, kpi.kpi_date, kpi.budget_variance_percentage,
        kpi.schedule_variance_days, kpi.quality_score, kpi.safety_incidents, kpi.client_satisfaction_score,
        kpi.team_productivity_percentage, kpi.cost_performance_index, kpi.schedule_performance_index, kpi.risk_level
    ))
    log_action(cursor, user["employee_id"], "Create", "KPI", kpi.kpi_id, f"Created KPI for project {kpi.project_id}")
    db.commit()
    cursor.execute("SELECT * FROM kpis WHERE kpi_id = ?", (kpi.kpi_id,))
    return dict(cursor.fetchone())


@router.put("/{kpi_id}", response_model=KPI)
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


@router.delete("/{kpi_id}", status_code=status.HTTP_204_NO_CONTENT)
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