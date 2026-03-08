import asyncio
from functools import partial
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from chat import answer_question

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class ChatRequest(BaseModel):
    message: str
    user_role: str = "employee"
    user_id: str = ""
    user_name: str = "User"
    last_exchange: dict = {}


@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")

    token = auth_header.replace("Bearer ", "").strip()

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

        return {"answer": answer}
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=503, detail="Assistant IA indisponible")