# app/routers/history.py
"""
Эндпоинты для управления историей чатов:
- Получение списка сессий
- Получение сообщений конкретной сессии
- Удаление сессии и всех её сообщений
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.routers.auth import get_current_username, get_db
from app.models import ChatSession, Message
from pydantic import BaseModel

router = APIRouter()

class SessionInfo(BaseModel):
    session_id: str
    name: str
    created_at: str  # ISO datetime as string

class MessageInfo(BaseModel):
    sender: str
    content: str
    timestamp: str  # ISO datetime as string

@router.get("/sessions", response_model=List[SessionInfo])
def list_sessions(username: str = Depends(get_current_username), db: Session = Depends(get_db)):
    """Возвращает список всех сессий чатов"""
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [SessionInfo(session_id=s.id, name=s.name, created_at=s.created_at.isoformat()) for s in sessions]

@router.get("/{session_id}", response_model=List[MessageInfo])
def get_session_messages(
    session_id: str,
    username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
) -> List[MessageInfo]:
    """Возвращает список сообщений для указанной сессии"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    messages = db.query(Message).filter(Message.chat_id == session_id).order_by(Message.timestamp.asc()).all()
    return [
        MessageInfo(
            sender=m.sender,
            content=m.content,
            timestamp=m.timestamp.isoformat()
        ) for m in messages
    ]

@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    username: str = Depends(get_current_username),
    db: Session = Depends(get_db),
):
    """Удаляет сессию и все её сообщения"""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    # Удалить сообщения
    db.query(Message).filter(Message.chat_id == session_id).delete()
    # Удалить саму сессию
    db.delete(session)
    db.commit()
    return {"message": f"Session '{session_id}' and its messages have been deleted."}
