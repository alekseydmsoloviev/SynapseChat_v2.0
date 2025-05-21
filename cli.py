# cli.py
import os
import typer
import subprocess
import webbrowser
from dotenv import load_dotenv, set_key
from sqlalchemy.orm import Session
from app.database import engine, Base, SessionLocal
from app.models import User

app = typer.Typer(invoke_without_command=True)

@app.callback(invoke_without_command=True)
def main():
    """
    Запуск админ-панели с управлением API-сервером.
    При первом старте: создаёт администратора и спрашивает порты.
    При последующих запусках берёт их из .env.
    """
    load_dotenv()

    # Создание таблиц, если не созданы
    Base.metadata.create_all(bind=engine)

    # 3) Первый запуск — создание админа и выбор портов
    db: Session = SessionLocal()
    try:
        admin = db.query(User).first()
        if not admin:
            typer.secho("Создание администратора:", fg=typer.colors.YELLOW)
            name = typer.prompt("Admin login")
            pwd  = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
            admin_port = typer.prompt("Admin panel port", default="8080")
            api_port   = typer.prompt("API server port", default="9000")
            admin = User(login=name, password=pwd)
            db.add(admin)
            db.commit()
            # Сохраняем порты
            env_path = os.path.join(os.getcwd(), ".env")
            open(env_path, "a").close()
            set_key(env_path, "ADMIN_PORT", admin_port)
            set_key(env_path, "PORT", api_port)
            typer.secho(
                f"Администратор '{name}' создан. "
                f"Admin panel: {admin_port}, API: {api_port}",
                fg=typer.colors.GREEN
            )
    finally:
        db.close()

    # 4) Читаем порты из .env
    load_dotenv()  # чтобы подхватить возможно обновлённые значения
    admin_port = os.getenv("ADMIN_PORT", "8080")
    api_port   = os.getenv("PORT",        "9000")

    # 5) Запуск админ-панели (она сама подхватит и запустит API на нужном порту)
    admin_cmd = [
        "uvicorn", "app.admin_app:app",
        "--host", "0.0.0.0", "--port", admin_port
    ]
    proc = subprocess.Popen(admin_cmd)

    # 6) Открываем в браузере
    webbrowser.open(f"http://localhost:{admin_port}/admin")

    try:
        proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        if proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    app()
