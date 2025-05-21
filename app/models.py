# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    login    = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class Model(Base):
    __tablename__ = "models"
    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id        = Column(String, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id  = Column(Integer, ForeignKey("models.id"), nullable=False)
    name      = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id        = Column(Integer, primary_key=True, index=True)
    chat_id   = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    sender    = Column(String, nullable=False)  # 'user' or 'ai'
    content   = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
