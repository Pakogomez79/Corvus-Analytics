"""Helpers de auditoría: inserción async/sin bloqueo de registros en `audit_logs`.

Uso:
  - En endpoints FastAPI: from fastapi import BackgroundTasks
    background_tasks.add_task(enqueue_audit, actor_id=..., actor_username=..., action=..., mensaje_es=...)

Funciones principales:
  - enqueue_audit(background_tasks, **kwargs): añade la tarea en background
  - write_audit(**kwargs): escribe directamente en la tabla (sincrónico)

Notas:
  - `before_state`, `after_state`, `extra` se serializan a JSON/strings y se redondean para PII.
  - `mensaje_es` es el texto legible en español para mostrar en la UI.
"""
from __future__ import annotations

import uuid
import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from fastapi import BackgroundTasks

from .db import engine
from .logger import get_logger

_logger = get_logger(__name__)


def _redact(d: Any) -> Any:
    """Redacta campos sensibles en un dict/valor simple.
    Reemplaza claves conocidas como 'password','token','password_hash' por '[REDACTED]'.
    """
    if d is None:
        return None
    if isinstance(d, dict):
        out = {}
        for k, v in d.items():
            kl = k.lower()
            if kl in ("password", "password_hash", "token", "api_key", "secret"):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(d, list):
        return [_redact(x) for x in d]
    return d


def _to_json_safe(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        # fallback to string
        try:
            return json.dumps(str(obj), ensure_ascii=False)
        except Exception:
            return None


def get_default_mensaje_es(actor_username: Optional[str], action: str, resource_type: Optional[str], resource_id: Optional[str]) -> str:
    actor = actor_username or "Usuario desconocido"
    res = f"{resource_type} {resource_id}" if resource_type or resource_id else "recurso"
    # Mensaje simple en español
    verb_map = {
        'user.create': 'creó',
        'user.update': 'actualizó',
        'user.delete': 'eliminó',
        'auth.login.success': 'inició sesión',
        'auth.login.failure': 'intento de acceso fallido para',
        'file.ingest.complete': 'finalizó ingestión de',
    }
    verbo = verb_map.get(action, 'ejecutó')
    # Ejemplos: "admin creó usuario 42"
    if action == 'auth.login.failure':
        return f"Intento de acceso fallido para '{resource_id}' desde {actor_username or 'IP desconocida'}"
    return f"{actor} {verbo} {res}"


def write_audit(
    actor_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    action: str = '',
    category: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    before_state: Any = None,
    after_state: Any = None,
    extra: Any = None,
    mensaje_es: Optional[str] = None,
    detalle_es: Any = None,
) -> None:
    """Escribe un registro de auditoría en la tabla `audit_logs`.

    Esta función es sincrónica; use `enqueue_audit` para ejecutarla en background.
    """
    # Preparar valores
    uid = str(uuid.uuid4())
    try:
        before_safe = _redact(before_state)
        after_safe = _redact(after_state)
        extra_safe = _redact(extra)
    except Exception:
        before_safe = None
        after_safe = None
        extra_safe = None

    before_json = _to_json_safe(before_safe)
    after_json = _to_json_safe(after_safe)
    extra_json = _to_json_safe(extra_safe)
    detalle_es_json = _to_json_safe(detalle_es)
    mensaje = mensaje_es or get_default_mensaje_es(actor_username, action, resource_type, resource_id)

    sql = (
        "INSERT INTO audit_logs (uuid, actor_id, actor_username, action, category, resource_type, resource_id, ip_address, user_agent, request_id, duration_ms, before_state, after_state, extra, mensaje_es, detalle_es)"
        " VALUES (:uuid, :actor_id, :actor_username, :action, :category, :resource_type, :resource_id, :ip_address, :user_agent, :request_id, :duration_ms, :before_state, :after_state, :extra, :mensaje_es, :detalle_es)"
    )

    params = {
        'uuid': uid,
        'actor_id': actor_id,
        'actor_username': actor_username,
        'action': action,
        'category': category,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'request_id': request_id,
        'duration_ms': duration_ms,
        'before_state': before_json,
        'after_state': after_json,
        'extra': extra_json,
        'mensaje_es': mensaje,
        'detalle_es': detalle_es_json,
    }

    # Ejecutar insert directamente
    try:
        with engine.begin() as conn:
                # Use SQLAlchemy text() so named parameters (':name') are bound correctly
                conn.execute(text(sql), params)
    except Exception as exc:
        # No fallar la aplicación por un error de auditoría; registrar el fallo para diagnóstico
        try:
            _logger.exception("Error escribiendo registro de auditoría: %s", exc)
        except Exception:
            # Silenciar cualquier error al loguear para evitar bucles
            pass


def enqueue_audit(background_tasks: BackgroundTasks, /, **kwargs) -> None:
    """Encola la escritura de auditoría para que se ejecute en background (FastAPI BackgroundTasks)."""
    background_tasks.add_task(write_audit, **kwargs)
