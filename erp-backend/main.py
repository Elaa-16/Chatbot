from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
import os

from core.database import get_db
from core.auth import authenticate_with_token, create_access_token, build_user_dict, log_action
from core.models import LoginRequest, LoginResponse, User
from passlib.hash import argon2

# ── Route imports ─────────────────────────────────────────────────────────────
from rag_engine.chatbot import router as chat_router
from api.routes.projects import router as projects_router
from api.routes.employees import router as employees_router
from api.routes.tasks import router as tasks_router
from api.routes.leave_requests import router as leave_router
from api.routes.kpis import router as kpis_router
from api.routes.other import (
    issues_router, equipment_router, suppliers_router, po_router,
    timesheets_router, notifications_router, documents_router,
    logs_router, stats_router, reports_router
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Construction ERP API", version="1.0.0")

ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(chat_router)
app.include_router(projects_router)
app.include_router(employees_router)
app.include_router(tasks_router)
app.include_router(leave_router)
app.include_router(kpis_router)
app.include_router(issues_router)
app.include_router(equipment_router)
app.include_router(suppliers_router)
app.include_router(po_router)
app.include_router(timesheets_router)
app.include_router(notifications_router)
app.include_router(documents_router)
app.include_router(logs_router)
app.include_router(stats_router)
app.include_router(reports_router)


# ── Core endpoints ────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    return {"message": "Construction ERP API", "version": "1.0.0"}


@app.get("/me", response_model=User)
def get_current_user(user: dict = Depends(authenticate_with_token)):
    return User(
        employee_id=user["employee_id"],
        username=user["username"],
        role=user["role"],
        assigned_projects=user["assigned_projects"],
        supervised_employees=user["supervised_employees"]
    )


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
    token_data = {
        "sub": user_data["username"],
        "employee_id": user_data["employee_id"],
        "role": user_data["role"]
    }
    access_token = create_access_token(token_data)
    log_action(cursor, user_data["employee_id"], "Login", "Auth", user_data["employee_id"],
               f"User {user_data['username']} logged in")
    db.commit()
    return {"access_token": access_token, "token_type": "bearer", "user": user_obj}


@app.post("/refresh-token")
def refresh_token(user: dict = Depends(authenticate_with_token)):
    token_data = {
        "sub": user["username"],
        "employee_id": user["employee_id"],
        "role": user["role"]
    }
    new_token = create_access_token(token_data)
    return {"access_token": new_token, "token_type": "bearer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)