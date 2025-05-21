import os
import sys
import subprocess
import secrets

from fastapi import (
    APIRouter, Request, Depends, Form,
    status, HTTPException
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dotenv import load_dotenv, dotenv_values, set_key
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User, ChatSession, Model, Message
from app.utils.ollama import list_installed_models, remove_model

router = APIRouter()
templates = Jinja2Templates(directory="templates")
ENV_PATH = os.path.join(os.getcwd(), ".env")
security = HTTPBasic()

# Глобальный процесс API
api_process: subprocess.Popen = None


def get_current_admin(
    creds: HTTPBasicCredentials = Depends(security)
):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.login == creds.username).first()
    db.close()
    if not user or not secrets.compare_digest(creds.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные креденшлы"
        )
    return user.login


@router.on_event("startup")
def start_api_server():
    """Запуск API-процесса при старте админ-приложения."""
    global api_process
    # Если API уже запущен, не запускаем второй процесс
    if api_process is not None:
        return
    load_dotenv(ENV_PATH)
    port = os.getenv("PORT", "8000")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.api_app:app", "--host", "0.0.0.0", "--port", port
    ]
    api_process = subprocess.Popen(cmd)


@router.get("/admin", response_class=HTMLResponse)
def dashboard(
    request: Request,
    admin: str = Depends(get_current_admin)
):
    cfg    = dotenv_values(ENV_PATH)
    port   = cfg.get("PORT", os.getenv("PORT", "8000"))

    db: Session = SessionLocal()
    try:
        users     = db.query(User).all()
        models    = list_installed_models()
        sessions  = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
        msg_counts = {
            s.id: db.query(Message)
                       .filter(Message.chat_id == s.id)
                       .count()
            for s in sessions
        }
    finally:
        db.close()

    return templates.TemplateResponse("admin.html", {
        "request":    request,
        "port":       port,
        "users":      users,
        "models":     models,
        "sessions":   sessions,
        "msg_counts": msg_counts,
    })


@router.post("/admin/config")
def update_config(
    port: str = Form(...),
    admin: str  = Depends(get_current_admin)
):
    open(ENV_PATH, "a").close()
    set_key(ENV_PATH, "PORT", port)
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/user")
def create_or_update_user(
    login_new: str = Form(...),
    password_new: str = Form(...),
    admin: str         = Depends(get_current_admin)
):
    db: Session = SessionLocal()
    try:
        u = db.query(User).filter(User.login == login_new).first()
        if u:
            u.password = password_new
        else:
            u = User(login=login_new, password=password_new)
            db.add(u)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/user/delete")
def delete_user(
    login_del: str = Form(...),
    admin: str        = Depends(get_current_admin)
):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.login == login_del).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        db.delete(user)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/clear")
def clear_database(
    admin: str = Depends(get_current_admin)
):
    """Очистить всю БД и удалить все установленные модели."""
    db: Session = SessionLocal()
    try:
        db.query(Message).delete()
        db.query(ChatSession).delete()
        db.query(Model).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()

    for model in list_installed_models():
        try:
            remove_model(model)
        except Exception:
            pass
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/restart")
def restart_api_server(
    admin: str = Depends(get_current_admin)
):
    """Перезапуск API-сервера на новом порту из .env."""
    global api_process

    # Убить процессы, слушающие старый порт
    old_cfg  = dotenv_values(ENV_PATH)
    old_port = old_cfg.get("PORT", "8000")
    try:
        out = subprocess.check_output(f'netstat -ano | findstr :{old_port}', shell=True, text=True)
        for line in out.splitlines():
            pid = line.split()[-1]
            subprocess.run(
                f'taskkill /PID {pid} /F', shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except subprocess.CalledProcessError:
        pass

    # Завершаем текущий процесс API
    if api_process and api_process.poll() is None:
        api_process.kill()
        api_process.wait(timeout=5)
        api_process = None

    # Запуск API на новом порту
    new_cfg  = dotenv_values(ENV_PATH)
    new_port = new_cfg.get("PORT", "8000")
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.api_app:app", "--host", "0.0.0.0", "--port", new_port
    ]
    api_process = subprocess.Popen(cmd)
    return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
