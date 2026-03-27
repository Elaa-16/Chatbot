from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from core.database import get_db
from core.auth import authenticate_with_token
from core.models import ApiWhitelist, ApiWhitelistCreate, ApiWhitelistUpdate

router = APIRouter(prefix="/whitelist", tags=["API Whitelist"])

@router.get("", response_model=List[ApiWhitelist])
def get_whitelist(db=Depends(get_db), user: dict = Depends(authenticate_with_token)):
    if user["role"] != "admin": raise HTTPException(status_code=403, detail="Admin only")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM api_whitelist")
    rows = cursor.fetchall()
    return [dict(r) for r in rows]

@router.post("", response_model=ApiWhitelist)
def create_whitelist_item(item: ApiWhitelistCreate, db=Depends(get_db), user: dict = Depends(authenticate_with_token)):
    if user["role"] != "admin": raise HTTPException(status_code=403, detail="Admin only")
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO api_whitelist (endpoint, methods, description, is_active)
        VALUES (?, ?, ?, ?)
    ''', (item.endpoint, item.methods, item.description, item.is_active))
    db.commit()
    new_id = cursor.lastrowid
    
    cursor.execute("SELECT * FROM api_whitelist WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    return dict(row)

@router.put("/{item_id}", response_model=ApiWhitelist)
def update_whitelist_item(item_id: int, item: ApiWhitelistUpdate, db=Depends(get_db), user: dict = Depends(authenticate_with_token)):
    if user["role"] != "admin": raise HTTPException(status_code=403, detail="Admin only")
    cursor = db.cursor()
    
    updates = {}
    if item.endpoint is not None: updates["endpoint"] = item.endpoint
    if item.methods is not None: updates["methods"] = item.methods
    if item.description is not None: updates["description"] = item.description
    if item.is_active is not None: updates["is_active"] = item.is_active
    
    if not updates:
        cursor.execute("SELECT * FROM api_whitelist WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row: raise HTTPException(status_code=404, detail="Item not found")
        return dict(row)
        
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values())
    values.append(item_id)
    
    cursor.execute(f"UPDATE api_whitelist SET {set_clause} WHERE id = ?", tuple(values))
    db.commit()
    
    cursor.execute("SELECT * FROM api_whitelist WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row: raise HTTPException(status_code=404, detail="Item not found")
    return dict(row)

@router.delete("/{item_id}")
def delete_whitelist_item(item_id: int, db=Depends(get_db), user: dict = Depends(authenticate_with_token)):
    if user["role"] != "admin": raise HTTPException(status_code=403, detail="Admin only")
    cursor = db.cursor()
    cursor.execute("DELETE FROM api_whitelist WHERE id = ?", (item_id,))
    db.commit()
    return {"message": "Item deleted successfully"}
