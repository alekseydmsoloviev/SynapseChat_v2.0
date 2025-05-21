# app/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Model, ChatSession, Message
from app.routers.auth import get_current_username
from app.utils.ollama import chat

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/{session_id}")
def send_message(
    session_id: str,
    payload: dict,
    username: str = Depends(get_current_username),
    db: Session = Depends(get_db)
):
    # Получаем пользователя
    user = db.query(User).filter(User.login == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Получаем или создаем модель
    model = db.query(Model).filter(Model.name == payload["model"]).first()
    if not model:
        model = Model(name=payload["model"])
        db.add(model)
        db.commit()
        db.refresh(model)

    # Создаем новую сессию, если её ещё нет
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        session = ChatSession(
            id=session_id,
            user_id=user.id,
            model_id=model.id,
            name=payload.get("chat_name", session_id)
        )
        db.add(session)
        db.commit()

    # Сохраняем сообщение пользователя
    user_msg = Message(
        chat_id=session_id,
        sender="user",
        content=payload["prompt"]
    )
    db.add(user_msg)
    db.commit()

    # Запрос к модели
    response_text = chat(
        session_id=session_id,
        model=model.name,
        prompt=payload["prompt"]
    )

    # Сохраняем ответ модели
    bot_msg = Message(
        chat_id=session_id,
        sender="ai",
        content=response_text
    )
    db.add(bot_msg)
    db.commit()

    return {"response": response_text}
