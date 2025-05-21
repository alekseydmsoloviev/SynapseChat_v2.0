# app/routers/models.py
"""
Эндпоинты для управления моделями Ollama:
- Список доступных и установленных моделей
- Установка модели
- Удаление модели
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict

from app.routers.auth import get_current_username
from app.utils.ollama import (
    list_remote_models,
    list_installed_models,
    install_model,
    remove_model,
)

router = APIRouter()

@router.get("", response_model=Dict[str, List[str]])
async def get_models(username: str = Depends(get_current_username)) -> Dict[str, List[str]]:
    """Возвращает списки доступных и локально установленных моделей"""
    try:
        available = list_remote_models()
        installed = list_installed_models()
        return {"available": available, "installed": installed}
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{name}/install")
async def install(name: str, username: str = Depends(get_current_username)) -> Dict[str, str]:
    """Устанавливает модель по её имени из публичного реестра"""
    try:
        install_model(name)
        return {"message": f"Model '{name}' installed successfully."}
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{name}")
async def uninstall(name: str, username: str = Depends(get_current_username)) -> Dict[str, str]:
    """Удаляет локально установленную модель"""
    try:
        remove_model(name)
        return {"message": f"Model '{name}' removed successfully."}
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
