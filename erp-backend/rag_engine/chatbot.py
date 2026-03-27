import asyncio
from functools import partial
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from core.database import get_db
from core.auth import log_action
from rag_engine.chat import answer_question

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


from datetime import datetime, timedelta

class ChatRequest(BaseModel):
    message: str
    user_role: str = "employee"
    user_id: str = ""
    user_name: str = "User"
    last_exchange: dict = {}

class AlertRequest(BaseModel):
    employee_id: str
    message: str

@router.post("/chat/alerts")
def add_chat_alert(data: AlertRequest, db=Depends(get_db)):
    try:
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO chat_alerts (employee_id, message)
            VALUES (?, ?)
        ''', (data.employee_id, data.message))
        db.commit()
        return {"status": "ok"}
    except Exception as e:
        print(f"Failed to add chat alert: {e}")
        raise HTTPException(status_code=500, detail="DB Error")

from core.auth import authenticate_with_token

@router.get("/chat/proactive")
def get_proactive_alerts(user: dict = Depends(authenticate_with_token), db=Depends(get_db)):
    try:
        cursor = db.cursor()
        
        # 1. Equipment maintenance alerts (Global)
        next_week_str = (datetime.now() + timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT equipment_id, name, next_maintenance 
            FROM equipment 
            WHERE next_maintenance IS NOT NULL 
              AND next_maintenance != ""
              AND status != 'Maintenance'
              AND next_maintenance <= ?
        ''', (next_week_str,))
        equipments = cursor.fetchall()
        
        alerts = []
        for eq in equipments:
            maint_date = eq["next_maintenance"]
            alerts.append({
                "id": f"alert_eq_{eq['equipment_id']}_{maint_date.split('T')[0]}",
                "message": f"🚨 **Alerte proactive** : L'équipement **{eq['name']}** ({eq['equipment_id']}) nécessite une maintenance avant le {maint_date.split('T')[0]}."
            })
            
        # 2. N8N specific alerts for this user
        employee_id = user.get("employee_id")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            SELECT id, message FROM chat_alerts 
            WHERE employee_id = ? AND is_read = 0
        ''', (employee_id,))
        user_alerts = cursor.fetchall()
        
        for ua in user_alerts:
            alerts.append({
                "id": f"n8n_alert_{ua['id']}",
                "message": ua["message"]
            })
            
            # Mark as read so it only shows once
            cursor.execute("UPDATE chat_alerts SET is_read = 1 WHERE id = ?", (ua["id"],))
        
        db.commit()
        return {"alerts": alerts}
    except Exception as e:
        print(f"Proactive logic error: {e}")
        return {"alerts": []}

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest, db=Depends(get_db)):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")

    token = auth_header.replace("Bearer ", "").strip()
    print(f"DEBUG chatbot token: {token[:30]}")

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")

    try:
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(
            None,
            partial(
                answer_question,
                question=body.message,
                user_role=body.user_role,
                user_id=body.user_id,
                user_name=body.user_name,
                token=token,
                last_exchange=body.last_exchange
            )
        )
        print("=== RAW ANSWER ===")
        print(repr(answer))
        print("==================")
        try:
            cursor = db.cursor()
            user_id = body.user_id if body.user_id else "UNKNOWN"
            log_action(cursor, user_id, "prompt", "assistant", user_id, f"Prompt: {body.message[:100]}")
            db.commit()
        except Exception as e:
            print(f"Failed to log prompt: {e}")

        return {"answer": answer}
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=503, detail="Assistant IA indisponible")