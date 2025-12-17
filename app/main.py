import io
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
import json
import uuid
import shutil

import pandas as pd
import pdfkit
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, Cookie, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from xhtml2pdf import pisa

from .auth import authenticate_user, create_access_token, decode_token, change_password, validate_password_strength, create_user, get_password_hash, has_permission
from .audit import enqueue_audit
from .canonical_mapping import resolve_canonical_concept
from .db import SessionLocal, engine
from .ingest_arelle import parse_xbrl
from .logger import get_logger, setup_application_logging
from .models import (
    Base,
    Entity,
    File as FileModel,
    Fact,
    Period,
    User,
    Role,
    UserRole,
    Permission,
    RolePermission,
    FinancialStatement,
    CanonicalLine,
)
from .pdf_config import PDF_OPTIONS, get_pdfkit_config
from .schemas import (
    FileResponse,
    FinancialStatementCreate,
    FinancialStatementResponse,
    CanonicalLineCreate,
    CanonicalLineResponse,
    CanonicalLineTree,
)

# Setup application logging
logger = setup_application_logging()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Path para almacenar configuración simple en JSON
SETTINGS_DIR = BASE_DIR / "config"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

def _ensure_settings_dir():
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def load_settings():
    _ensure_settings_dir()
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}

def save_settings(data: dict):
    _ensure_settings_dir()
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.exception("Error guardando settings: %s", e)
        return False


def _normalize_logo_url(settings: dict) -> str:
    """Normalize a stored logo path to a public URL.

    - If already an absolute URL (http/https) or starts with '/', return as-is.
    - If the value is a filesystem path (absolute or relative) that contains 'static',
      convert it to a '/static/...' URL.
    - If path is under BASE_DIR, return the relative path starting with '/'.
    """
    url = settings.get("logo_url") if isinstance(settings, dict) else ''
    if not url:
        return ''
    url = str(url)
    if url.startswith("http://") or url.startswith("https://") or url.startswith("/"):
        return url

    sp = url.replace('\\', '/')

    # if contains 'static/', build public path
    if 'static/' in sp:
        idx = sp.index('static/')
        return '/' + sp[idx:]

    # if absolute path under project
    try:
        p = Path(sp)
        if p.is_absolute() and p.exists():
            s = str(p).replace('\\', '/')
            base = str(BASE_DIR).replace('\\', '/')
            if s.startswith(base):
                rel = s[len(base):]
                rel = rel if rel.startswith('/') else '/' + rel
                return rel
    except Exception:
        pass

    # fallback: return original value
    return url

# Helper disponible en plantillas para comprobar permisos dinámicamente
def _template_has_permission(request: Request, permission_name: str) -> bool:
    # intenta leer token desde la cookie y verificar permiso en DB
    access_token = request.cookies.get('access_token') or ''
    token = access_token[7:] if access_token.startswith('Bearer ') else access_token
    payload = decode_token(token) if token else None
    if not payload:
        return False
    user_id = payload.get('user_id')
    if not user_id:
        return False
    db = SessionLocal()
    try:
        return has_permission(db, user_id, permission_name)
    finally:
        db.close()

# Registrar helper en el entorno de Jinja
try:
    TEMPLATES.env.globals['has_permission'] = _template_has_permission
except Exception:
    # en entornos donde env no está disponible, ignorar silenciosamente
    pass


def _template_get_current_user(request: Optional[Request]):
    """
    Helper para plantillas: devuelve un diccionario con datos del usuario actual
    (name, initials, role) leyendo el token desde la cookie y consultando la DB.
    """
    if not request:
        return None
    access_token = request.cookies.get('access_token') or ''
    token = access_token[7:] if access_token.startswith('Bearer ') else access_token
    payload = decode_token(token) if token else None
    if not payload:
        return None
    user_id = payload.get('user_id')
    # valores por defecto basados en token
    result = {
        'name': payload.get('sub') or 'Usuario',
        'initials': 'US',
        'role': None,
    }
    if not user_id:
        return result
    db = SessionLocal()
    try:
        user = db.query(User).get(user_id)
        if not user:
            return result
        # nombre a mostrar: preferir nombre + apellido si existen
        if (user.first_name and user.first_name.strip()) or (user.last_name and user.last_name.strip()):
            name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
        else:
            name = user.username
        # iniciales: primeras letras de nombre y apellido o de username
        parts = name.split()
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[1][0]).upper()
        else:
            initials = (name[0] if name else 'U').upper()
        # rol: tomar el primer rol asignado si existe
        role_obj = db.query(Role).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).first()
        role_name = role_obj.name if role_obj else None
        result.update({'name': name, 'initials': initials, 'role': role_name})
        return result
    except Exception:
        return result
    finally:
        try:
            db.close()
        except Exception:
            pass

try:
    TEMPLATES.env.globals['get_current_user'] = _template_get_current_user
except Exception:
    pass


# Helper para determinar el módulo del breadcrumb a partir de active_page
def _breadcrumb_module(active_page: Optional[str]) -> str:
    if not active_page:
        return ""
    mapping = {
        # Principal
        'dashboard': 'Principal',
        # XBRL
        'upload': 'XBRL',
        'entidades': 'XBRL',
        'archivos': 'XBRL',
        # Reportes / Análisis
        'comparativos': 'Reportes',
        'balance': 'Reportes',
        'resultados': 'Reportes',
        'indicadores': 'Reportes',
        # Administración
        'usuarios': 'Administración',
        'users': 'Administración',
        'roles': 'Administración',
        'permisos': 'Administración',
        'auditoria': 'Administración',
        'configuracion': 'Administración',
        # Export / Otros
        'upload': 'XBRL',
    }
    return mapping.get(active_page, active_page.capitalize())

try:
    TEMPLATES.env.globals['breadcrumb_module'] = _breadcrumb_module
except Exception:
    pass


def _get_request_ip_ua(request: Optional[Request]):
    """Extrae IP y User-Agent de la request, respetando X-Forwarded-For si existe."""
    if not request:
        return None, None
    xff = request.headers.get('x-forwarded-for') or request.headers.get('X-Forwarded-For')
    if xff:
        ip = xff.split(',')[0].strip()
    else:
        client = getattr(request, 'client', None)
        ip = client.host if client is not None else None
    ua = request.headers.get('user-agent')
    return ip, ua


def _enqueue_with_request(background_tasks: BackgroundTasks, request: Optional[Request], **kwargs):
    ip, ua = _get_request_ip_ua(request)
    try:
        enqueue_audit(background_tasks, ip_address=ip, user_agent=ua, **kwargs)
    except Exception:
        # no propagar errores de auditoría
        pass
# Instancia de FastAPI y configuración
app = FastAPI(title="Corvus International Group")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# XBRL Canonical lines endpoints
# -----------------------------


@app.get('/xbrl/canonical', response_class=HTMLResponse)
def view_canonical(request: Request, db=Depends(get_db)):
    # Página Jinja que contiene el árbol y herramientas de import/CRUD
    statements = db.query(FinancialStatement).order_by(FinancialStatement.code).all()
    return TEMPLATES.TemplateResponse('canonical_lines.html', {'request': request, 'statements': statements, 'active_page': 'canonical'})


@app.get('/api/xbrl/statements')
def api_list_statements(db=Depends(get_db)):
    stmts = db.query(FinancialStatement).order_by(FinancialStatement.code).all()
    return [FinancialStatementResponse.from_orm(s) for s in stmts]


@app.post('/api/xbrl/statements')
def api_create_statement(item: FinancialStatementCreate, db=Depends(get_db)):
    stmt = FinancialStatement(code=item.code, name=item.name, type=item.type)
    db.add(stmt)
    try:
        db.commit()
        db.refresh(stmt)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return FinancialStatementResponse.from_orm(stmt)


def _build_tree(db, statement_id: int):
    rows = db.query(CanonicalLine).filter(CanonicalLine.statement_id == statement_id).order_by(CanonicalLine.parent_id.nullsfirst(), CanonicalLine.order.nullsfirst()).all()
    nodes = {r.id: {'id': r.id, 'code': r.code, 'name': r.name, 'order': r.order, 'children': []} for r in rows}
    root = []
    for r in rows:
        if r.parent_id and r.parent_id in nodes:
            nodes[r.parent_id]['children'].append(nodes[r.id])
        else:
            root.append(nodes[r.id])
    return root


@app.get('/api/xbrl/statements/{statement_id}/lines/tree')
def api_statement_tree(statement_id: int, db=Depends(get_db)):
    tree = _build_tree(db, statement_id)
    return tree


@app.post('/api/xbrl/lines')
def api_create_line(item: CanonicalLineCreate, db=Depends(get_db)):
    # require that statement exists (user requested manual creation prior)
    stmt = db.query(FinancialStatement).get(item.statement_id)
    if not stmt:
        raise HTTPException(status_code=400, detail='FinancialStatement not found')
    line = CanonicalLine(code=item.code, name=item.name, statement_id=item.statement_id, parent_id=item.parent_id, order=item.order)
    # map metadata field if provided
    if item.metadata is not None:
        # attribute name on model is 'meta'
        line.meta = item.metadata
    db.add(line)
    try:
        db.commit()
        db.refresh(line)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return CanonicalLineResponse.from_orm(line)


@app.put('/api/xbrl/lines/{line_id}')
def api_update_line(line_id: int, item: CanonicalLineCreate, db=Depends(get_db)):
    line = db.query(CanonicalLine).get(line_id)
    if not line:
        raise HTTPException(status_code=404, detail='Line not found')
    line.code = item.code
    line.name = item.name
    line.parent_id = item.parent_id
    line.order = item.order
    if item.metadata is not None:
        line.meta = item.metadata
    try:
        db.commit()
        db.refresh(line)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return CanonicalLineResponse.from_orm(line)


@app.delete('/api/xbrl/lines/{line_id}')
def api_delete_line(line_id: int, db=Depends(get_db)):
    line = db.query(CanonicalLine).get(line_id)
    if not line:
        raise HTTPException(status_code=404, detail='Line not found')
    # prevent deletion if facts linked
    linked = db.query(Fact).filter(Fact.canonical_line_id == line.id).first()
    if linked:
        raise HTTPException(status_code=400, detail='Cannot delete line with linked facts')
    db.delete(line)
    db.commit()
    return {'ok': True}


@app.patch('/api/xbrl/lines/{line_id}/move')
def api_move_line(line_id: int, payload: dict, db=Depends(get_db)):
    # payload expected: { new_parent_id: int|null, new_order: int }
    new_parent_id = payload.get('new_parent_id')
    new_order = payload.get('new_order')
    if new_order is None:
        raise HTTPException(status_code=400, detail='new_order is required')
    line = db.query(CanonicalLine).get(line_id)
    if not line:
        raise HTTPException(status_code=404, detail='Line not found')

    # If moving under a parent, ensure parent exists and same statement
    if new_parent_id is not None:
        parent = db.query(CanonicalLine).get(new_parent_id)
        if not parent:
            raise HTTPException(status_code=400, detail='New parent not found')
        if parent.statement_id != line.statement_id:
            raise HTTPException(status_code=400, detail='Cannot move across statements')
        # Prevent cycles: walk ancestors of parent to ensure none equals line
        cur = parent
        while cur is not None:
            if cur.id == line.id:
                raise HTTPException(status_code=400, detail='Invalid move: would create cycle')
            cur = cur.parent

    # apply new parent
    line.parent_id = new_parent_id

    # rebuild sibling order under new_parent
    siblings = db.query(CanonicalLine).filter(
        CanonicalLine.statement_id == line.statement_id,
        CanonicalLine.parent_id == new_parent_id,
        CanonicalLine.id != line.id,
    ).order_by(CanonicalLine.order.nullsfirst(), CanonicalLine.id).all()

    insert_index = max(0, int(new_order) - 1)
    # build new ordered list
    ordered = []
    for i, s in enumerate(siblings):
        ordered.append(s)
    if insert_index >= len(ordered):
        ordered.append(line)
    else:
        ordered.insert(insert_index, line)

    # reassign orders sequentially starting at 1
    for idx, node in enumerate(ordered, start=1):
        node.order = idx

    try:
        db.commit()
        db.refresh(line)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return CanonicalLineResponse.from_orm(line)


def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
    db = Depends(get_db)
) -> Optional[dict]:
    """
    Obtiene el usuario actual desde el token en la cookie
    Redirige al login si no hay token válido
    """
    if not access_token:
        return None
    
    # Extraer el token (formato: "Bearer <token>")
    if access_token.startswith("Bearer "):
        token = access_token[7:]
    else:
        token = access_token
    
    # Decodificar token
    payload = decode_token(token)
    
    if not payload:
        return None
    
    return payload


def require_permission(permission_name: str):
    """Dependency generator that checks if current user has the required permission.
    Returns a FastAPI dependency that raises 403 or redirects to login.
    """
    def _require(current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db)):
        if not current_user:
            # No user -> redirect to login
            return RedirectResponse(url="/login", status_code=303)
        user_id = current_user.get("user_id")
        if not has_permission(db, user_id, permission_name):
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return True
    return _require


# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Muestra la página de login y fuerza no-cache"""
    response = TEMPLATES.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/api/session")
def api_session(current_user: Optional[dict] = Depends(get_current_user)):
    """Endpoint que valida si la sesión es válida (usa cookie HttpOnly)."""
    if not current_user:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    return JSONResponse(status_code=200, content={"ok": True})
@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    background_tasks: BackgroundTasks,
    username: str = Form(...),
    password: str = Form(...),
    db = Depends(get_db),
):
    """Procesa el login del usuario y genera token JWT"""
    
    # Autenticar usuario
    user = authenticate_user(db, username, password)
    
    if not user:
        logger.warning(f"Intento de login fallido para usuario: {username}")
        try:
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_username=username, action='auth.login.failure', category='auth', mensaje_es=f"Intento de acceso fallido para '{username}'")
        except Exception:
            pass
        return TEMPLATES.TemplateResponse("login.html", {
            "request": request,
            "error": "Usuario o contraseña incorrectos"
        }, status_code=401)
    
    # Crear token JWT
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    logger.info(f"Login exitoso para usuario: {username}")
    
    # Redirigir explícitamente al dashboard con el token en cookie
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutos
        samesite="lax"
    )
    
    try:
        if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=user.id, actor_username=user.username, action='auth.login.success', category='auth', resource_type='user', resource_id=str(user.id), mensaje_es=f"{user.username} inició sesión")
    except Exception:
        pass

    return response


@app.get("/logout")
async def logout(request: Request, background_tasks: BackgroundTasks, current_user: Optional[dict] = Depends(get_current_user)):
    """Cierra la sesión del usuario eliminando el token y fuerza no-cache"""
    logger.info("Usuario cerró sesión")
    try:
        if current_user and background_tasks is not None:
            _enqueue_with_request(background_tasks, request, actor_id=current_user.get("user_id"), actor_username=current_user.get("sub"), action='auth.logout', category='auth', mensaje_es=f"{current_user.get('sub')} cerró sesión")
    except Exception:
        pass
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    error: Optional[str] = None,
    success: Optional[str] = None
):
    """Muestra la página para cambiar contraseña"""
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    response = TEMPLATES.TemplateResponse("change_password.html", {
        "request": request,
        "error": error,
        "success": success
    })
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/configuracion", response_class=HTMLResponse)
def configuracion_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    permission_ok: bool = Depends(require_permission('config.manage')),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    settings = load_settings() or {}
    # normalizar ruta de logo a URL pública si es una ruta local
    settings["logo_url"] = _normalize_logo_url(settings)
    return TEMPLATES.TemplateResponse("configuracion.html", {"request": request, "settings": settings, "active_page": "configuracion"})


@app.post("/configuracion", response_class=HTMLResponse)
def configuracion_submit(
    request: Request,
    company_name: Optional[str] = Form(None),
    date_format: Optional[str] = Form(None),
    currency: Optional[str] = Form(None),
    logo_url: Optional[str] = Form(None),
    logo_file: UploadFile = File(None),
    current_user: Optional[dict] = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    settings = load_settings() or {}

    # Si se subió un archivo de logo, guardarlo en static/images y usar su ruta
    previous_logo = settings.get("logo_url", "")
    if logo_file is not None and getattr(logo_file, 'filename', ''):
        try:
            images_dir = BASE_DIR / "static" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            orig_name = Path(logo_file.filename).name
            ext = Path(orig_name).suffix.lower()
            allowed = {'.png', '.jpg', '.jpeg', '.svg', '.gif'}
            if ext not in allowed:
                return TEMPLATES.TemplateResponse("configuracion.html", {"request": request, "settings": settings, "error": "Tipo de archivo no permitido para el logo.", "active_page": "configuracion"})
            # Usar nombre fijo para el logo: logo.png (sobrescribe si existe)
            filename = "logo.png"
            dest_path = images_dir / filename
            with open(dest_path, 'wb') as out_f:
                shutil.copyfileobj(logo_file.file, out_f)

            # establecer ruta pública relativa
            settings["logo_url"] = f"/static/images/{filename}"
        except Exception as e:
            logger.exception("Error guardando logo: %s", e)
            return TEMPLATES.TemplateResponse("configuracion.html", {"request": request, "settings": settings, "error": "Error guardando el archivo del logo.", "active_page": "configuracion"})
    else:
        # mantener o actualizar URL manual
        settings["logo_url"] = logo_url or settings.get("logo_url", "")

    settings.update({
        "company_name": company_name or settings.get("company_name", ""),
        "date_format": date_format or settings.get("date_format", "YYYY-MM-DD"),
        "currency": currency or settings.get("currency", "USD"),
    })

    ok = save_settings(settings)
    if ok:
        try:
            actor_id = current_user.get("user_id")
            actor_username = current_user.get("sub") or current_user.get("username")
            _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='config.update', category='config', resource_type='settings', resource_id='site', mensaje_es=f"{actor_username} actualizó configuración general")
        except Exception:
            pass
        # Normalizar logo_url antes de mostrar
        settings["logo_url"] = _normalize_logo_url(settings)
        return TEMPLATES.TemplateResponse("configuracion.html", {"request": request, "settings": settings, "success": "Configuración guardada correctamente", "active_page": "configuracion"})

    return TEMPLATES.TemplateResponse("configuracion.html", {"request": request, "settings": settings, "error": "Error guardando configuración", "active_page": "configuracion"})


@app.post("/change-password", response_class=HTMLResponse)
async def change_password_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user),
    db = Depends(get_db),
):
    """Procesa el cambio de contraseña"""
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Validar que las nuevas contraseñas coincidan
    if new_password != confirm_password:
        response = TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": "Las contraseñas nuevas no coinciden"
        }, status_code=400)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Validar fortaleza de la contraseña
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        response = TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": message
        }, status_code=400)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Cambiar contraseña
    user_id = current_user.get("user_id")
    success = change_password(db, user_id, current_password, new_password)

    if success:
        logger.info(f"Contraseña cambiada para usuario ID: {user_id}")
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='user.password.change', category='users', resource_type='user', resource_id=str(user_id), mensaje_es=f"{actor_username} cambió su contraseña")
        except Exception:
            pass
        # Forzar re-login: eliminar cookie y redirigir a login
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="access_token")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    else:
        response = TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": "Contraseña actual incorrecta"
        }, status_code=400)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# ============================================================================
# RUTAS EXISTENTES
# ============================================================================

def _format_period(period_start: Optional[date], period_end: Optional[date]) -> str:
    if period_start and period_end:
        return f"{period_start} a {period_end}"
    if period_end:
        return f"Instante: {period_end}"
    if period_start:
        return f"Desde: {period_start}"
    return "N/A"


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _fetch_comparativos_rows(
    db,
    entidad: Optional[str],
    concepto: Optional[str],
    period_start: Optional[date],
    period_end: Optional[date],
) -> List[dict]:
    query = (
        db.query(
            Entity.name.label("entidad"),
            Period.start.label("period_start"),
            Period.end.label("period_end"),
            Fact.canonical_concept.label("canonical_concept"),
            Fact.concept_qname.label("concept_qname"),
            Fact.value.label("valor"),
            Fact.currency.label("fact_currency"),
            FileModel.currency.label("file_currency"),
        )
        .select_from(Fact)
        .join(FileModel, Fact.file)
        .join(Entity, FileModel.entity)
        .join(Period, FileModel.period)
        .filter(Fact.value.isnot(None))
    )

    if entidad:
        query = query.filter(Entity.name.ilike(f"%{entidad}%"))
    if concepto:
        pattern = f"%{concepto}%"
        query = query.filter(
            or_(
                Fact.canonical_concept.ilike(pattern),
                Fact.concept_qname.ilike(pattern),
            )
        )
    if period_start:
        query = query.filter(or_(Period.start >= period_start, Period.end >= period_start))
    if period_end:
        query = query.filter(or_(Period.start <= period_end, Period.end <= period_end))

    rows = []
    for row in query.order_by(Period.end.desc(), Entity.name).all():
        periodo = _format_period(row.period_start, row.period_end)
        moneda = row.fact_currency or row.file_currency or "N/A"
        valor = _decimal_to_float(row.valor)
        rows.append(
            {
                "entidad": row.entidad,
                "periodo": periodo,
                "concepto": row.canonical_concept or row.concept_qname,
                "valor": valor,
                "moneda": moneda,
            }
        )
    return rows


def _rows_to_dataframe(rows: List[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["entidad", "periodo", "concepto", "valor", "moneda"])
    return pd.DataFrame(rows)


@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    # Verificar autenticación
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    # Redirigir al dashboard centralizado
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/mi-perfil", response_class=HTMLResponse)
def my_profile_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
):
    """Página para ver/editar el propio perfil del usuario."""
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    user_id = current_user.get("user_id")
    user = db.query(User).filter(User.id == user_id).options(joinedload(User.roles).joinedload(UserRole.role)).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    # Construir payload de usuario para la plantilla
    roles = [ur.role.name for ur in user.roles if ur.role]
    full_name = "".join(filter(None, [user.first_name or "", (" " + user.last_name) if user.last_name else ""]))
    if not full_name.strip():
        full_name = user.username
    # Calcular iniciales: preferir nombre + apellido, fallback a primeras letras del username
    initials = None
    if user.first_name and user.last_name:
        initials = (user.first_name[:1] + user.last_name[:1]).upper()
    elif user.first_name:
        initials = user.first_name[:2].upper()
    else:
        initials = (user.username[:2] if user.username else "US").upper()

    user_payload = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_active": bool(user.is_active),
        "must_change_password": bool(user.must_change_password),
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else None,
        "roles": roles,
        "name": full_name,
        "initials": initials,
    }

    return TEMPLATES.TemplateResponse("user_profile.html", {"request": request, "user": user_payload})


@app.post("/mi-perfil", response_class=HTMLResponse)
def my_profile_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
):
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    user_id = current_user.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        db.commit()
        try:
            actor_id = user.id
            actor_username = user.username
            _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='user.profile.update', category='users', resource_type='user', resource_id=str(user.id), mensaje_es=f"{actor_username} actualizó su perfil")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        # Recalcular payload para renderizar con los valores intentados
        roles = [ur.role.name for ur in user.roles if ur.role]
        full_name = "".join(filter(None, [first_name or "", (" " + (last_name or "")) if last_name else ""]))
        if not full_name.strip():
            full_name = user.username
        initials = None
        if first_name and last_name:
            initials = (first_name[:1] + last_name[:1]).upper()
        elif first_name:
            initials = first_name[:2].upper()
        else:
            initials = (user.username[:2] if user.username else "US").upper()

        user_payload = {
            "id": user.id,
            "username": user.username,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "is_active": bool(user.is_active),
            "must_change_password": bool(user.must_change_password),
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else None,
            "roles": roles,
            "name": full_name,
            "initials": initials,
        }
        return TEMPLATES.TemplateResponse("user_profile.html", {"request": request, "user": user_payload, "error": str(e)})

    # Recalcular payload con valores guardados
    roles = [ur.role.name for ur in user.roles if ur.role]
    full_name = "".join(filter(None, [user.first_name or "", (" " + user.last_name) if user.last_name else ""]))
    if not full_name.strip():
        full_name = user.username
    if user.first_name and user.last_name:
        initials = (user.first_name[:1] + user.last_name[:1]).upper()
    elif user.first_name:
        initials = user.first_name[:2].upper()
    else:
        initials = (user.username[:2] if user.username else "US").upper()

    user_payload = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_active": bool(user.is_active),
        "must_change_password": bool(user.must_change_password),
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else None,
        "roles": roles,
        "name": full_name,
        "initials": initials,
    }

    return TEMPLATES.TemplateResponse("user_profile.html", {"request": request, "user": user_payload, "success": "Perfil actualizado correctamente"})


# ============================================================================
# RUTAS DE GESTIÓN DE USUARIOS (CRUD)
# ============================================================================


def _require_admin(current_user: Optional[dict], db) -> bool:
    if not current_user:
        return False
    user_id = current_user.get("user_id")
    if not user_id:
        return False
    user = db.query(User).filter(User.id == user_id).options(joinedload(User.roles).joinedload(UserRole.role)).first()
    if not user:
        return False
    for ur in user.roles:
        if ur.role and ur.role.name == "admin":
            return True
    return False


@app.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db=Depends(get_db),
    permission_ok: bool = Depends(require_permission('users.view')),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    # Server-side search filter
    query = db.query(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter(User.username.ilike(like_q))

    total = query.count()
    per_page = 10
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    users = query.order_by(User.username).offset((page - 1) * per_page).limit(per_page).all()
    users_data = []
    for u in users:
        roles = [ur.role.name for ur in u.roles if ur.role]
        users_data.append({
            "id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "roles": ", ".join(roles),
            "phone": u.phone,
            "must_change_password": u.must_change_password,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "N/A",
        })

    return TEMPLATES.TemplateResponse(
        "users.html",
        {
            "request": request,
            "users": users_data,
            "active_page": "users",
            "q": q or "",
            "page": page,
            "pages": pages,
            "total": total,
            "per_page": per_page,
        },
    )


@app.get("/users/create", response_class=HTMLResponse)
def users_create_page(request: Request, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('users.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    return TEMPLATES.TemplateResponse("user_form.html", {"request": request, "action": "create", "user": None})


@app.post("/users/create", response_class=HTMLResponse)
def users_create_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    username: str = Form(...),
    password: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    must_change_password: Optional[bool] = Form(False),
    is_active: Optional[bool] = Form(True),
    roles: Optional[str] = Form(""),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Sólo admin puede crear usuarios
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    # Crear usuario
    try:
        new_user = create_user(db=db, username=username, password=password, first_name=first_name, last_name=last_name, phone=phone, must_change_password=bool(must_change_password))
        new_user.is_active = bool(is_active)

        # Asignar roles (coma-separados)
        role_names = [r.strip() for r in (roles or "").split(",") if r.strip()]
        for rn in role_names:
            role = db.query(Role).filter(Role.name == rn).first()
            if not role:
                role = Role(name=rn)
                db.add(role)
                db.commit()
                db.refresh(role)
            assoc = UserRole(user_id=new_user.id, role_id=role.id)
            db.add(assoc)

        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='user.create', category='users', resource_type='user', resource_id=str(new_user.id), mensaje_es=f"{actor_username} creó el usuario {username}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("user_form.html", {"request": request, "action": "create", "error": str(e), "user": {"username": username, "is_active": is_active, "roles": roles}} , status_code=400)

    return RedirectResponse(url="/users", status_code=303)


@app.get("/users/{user_id}/edit", response_class=HTMLResponse)
def users_edit_page(request: Request, user_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('users.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/users", status_code=303)

    roles = ", ".join([ur.role.name for ur in user.roles if ur.role])
    return TEMPLATES.TemplateResponse("user_form.html", {"request": request, "action": "edit", "user": {"id": user.id, "username": user.username, "is_active": user.is_active, "roles": roles, "first_name": user.first_name, "last_name": user.last_name, "phone": user.phone, "must_change_password": user.must_change_password}})


@app.post("/users/{user_id}/edit", response_class=HTMLResponse)
def users_edit_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: int,
    username: str = Form(...),
    password: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    must_change_password: Optional[bool] = Form(False),
    is_active: Optional[bool] = Form(True),
    roles: Optional[str] = Form(""),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/users", status_code=303)

    try:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.phone = phone
        user.must_change_password = bool(must_change_password)
        user.is_active = bool(is_active)
        if password:
            user.password_hash = get_password_hash(password)

        # Actualizar roles: borrar existentes y crear nuevas asociaciones
        db.query(UserRole).filter(UserRole.user_id == user.id).delete()
        role_names = [r.strip() for r in (roles or "").split(",") if r.strip()]
        for rn in role_names:
            role = db.query(Role).filter(Role.name == rn).first()
            if not role:
                role = Role(name=rn)
                db.add(role)
                db.commit()
                db.refresh(role)
            assoc = UserRole(user_id=user.id, role_id=role.id)
            db.add(assoc)

        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='user.update', category='users', resource_type='user', resource_id=str(user.id), mensaje_es=f"{actor_username} actualizó el usuario {username}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("user_form.html", {"request": request, "action": "edit", "error": str(e), "user": {"id": user.id, "username": username, "is_active": is_active, "roles": roles}} , status_code=400)

    return RedirectResponse(url="/users", status_code=303)


@app.post("/users/{user_id}/delete")
def users_delete(request: Request, background_tasks: BackgroundTasks, user_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('users.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado"})

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"detail": "Usuario no encontrado"})

    try:
        username = user.username
        db.delete(user)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='user.delete', category='users', resource_type='user', resource_id=str(user_id), mensaje_es=f"{actor_username} eliminó el usuario {username}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})

    return RedirectResponse(url="/users", status_code=303)


# Rutas alias en español para compatibilidad con plantillas antiguas
@app.get("/usuarios", response_class=HTMLResponse)
def usuarios_page_alias(request: Request, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('users.view'))):
    return RedirectResponse(url="/users", status_code=303)


@app.get("/usuarios/create", response_class=HTMLResponse)
def usuarios_create_alias(request: Request, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('users.manage'))):
    return RedirectResponse(url="/users/create", status_code=303)


@app.get("/usuarios/{user_id}/edit", response_class=HTMLResponse)
def usuarios_edit_alias(request: Request, user_id: int):
    return RedirectResponse(url=f"/users/{user_id}/edit", status_code=303)


@app.post("/usuarios/{user_id}/delete")
def usuarios_delete_alias(request: Request, user_id: int):
    return RedirectResponse(url=f"/users/{user_id}/delete", status_code=303)


# ============================================================================
# RUTAS DE GESTIÓN DE ROLES
# ============================================================================


@app.get("/roles", response_class=HTMLResponse)
def roles_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db=Depends(get_db),
    permission_ok: bool = Depends(require_permission('roles.view')),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    query = db.query(Role)
    if q:
        like_q = f"%{q}%"
        query = query.filter(Role.name.ilike(like_q))

    total = query.count()
    per_page = 10
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    roles = query.order_by(Role.name).offset((page - 1) * per_page).limit(per_page).all()
    roles_data = []
    for r in roles:
        perms = [rp.permission.name for rp in r.permissions if rp.permission]
        roles_data.append({
            "id": r.id,
            "name": r.name,
            "permissions": ", ".join(perms),
        })

    return TEMPLATES.TemplateResponse(
        "roles.html",
        {
            "request": request,
            "roles": roles_data,
            "active_page": "roles",
            "q": q or "",
            "page": page,
            "pages": pages,
            "total": total,
            "per_page": per_page,
        },
    )


@app.get("/roles/create", response_class=HTMLResponse)
def roles_create_page(request: Request, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    permissions = db.query(Permission).order_by(Permission.name).all()
    perms_list = [p.name for p in permissions]
    db.close()
    return TEMPLATES.TemplateResponse("role_form.html", {"request": request, "action": "create", "role": None, "permissions": perms_list})


@app.post("/roles/create", response_class=HTMLResponse)
def roles_create_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    permissions: Optional[str] = Form(""),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    try:
        role = Role(name=name)
        db.add(role)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='role.create', category='roles', resource_type='role', resource_id=str(role.id), mensaje_es=f"{actor_username} creó el rol {name}")
        except Exception:
            pass
        db.refresh(role)

        perm_names = [p.strip() for p in (permissions or "").split(",") if p.strip()]
        for pn in perm_names:
            perm = db.query(Permission).filter(Permission.name == pn).first()
            if not perm:
                perm = Permission(name=pn)
                db.add(perm)
                db.commit()
                db.refresh(perm)
            assoc = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(assoc)
        db.commit()
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("role_form.html", {"request": request, "action": "create", "error": str(e), "role": {"name": name, "permissions": permissions}}, status_code=400)

    return RedirectResponse(url="/roles", status_code=303)


@app.get("/roles/{role_id}/edit", response_class=HTMLResponse)
def roles_edit_page(request: Request, role_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return RedirectResponse(url="/roles", status_code=303)

    perms = ", ".join([rp.permission.name for rp in role.permissions if rp.permission])
    all_perms = [p.name for p in db.query(Permission).order_by(Permission.name).all()]
    return TEMPLATES.TemplateResponse("role_form.html", {"request": request, "action": "edit", "role": {"id": role.id, "name": role.name, "permissions": perms}, "permissions": all_perms})


@app.post("/roles/{role_id}/edit", response_class=HTMLResponse)
def roles_edit_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    role_id: int,
    name: str = Form(...),
    permissions: Optional[str] = Form(""),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return RedirectResponse(url="/roles", status_code=303)

    try:
        role.name = name
        # Update permissions: remove existing and add new
        db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
        perm_names = [p.strip() for p in (permissions or "").split(",") if p.strip()]
        for pn in perm_names:
            perm = db.query(Permission).filter(Permission.name == pn).first()
            if not perm:
                perm = Permission(name=pn)
                db.add(perm)
                db.commit()
                db.refresh(perm)
            assoc = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(assoc)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='role.update', category='roles', resource_type='role', resource_id=str(role.id), mensaje_es=f"{actor_username} actualizó el rol {name}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("role_form.html", {"request": request, "action": "edit", "error": str(e), "role": {"id": role.id, "name": name, "permissions": permissions}}, status_code=400)

    return RedirectResponse(url="/roles", status_code=303)


@app.post("/roles/{role_id}/delete")
def roles_delete(request: Request, background_tasks: BackgroundTasks, role_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado"})

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        return JSONResponse(status_code=404, content={"detail": "Rol no encontrado"})

    # Verificar usuarios asignados al rol
    assigned_count = db.query(UserRole).filter(UserRole.role_id == role.id).count()
    if assigned_count > 0:
        # Preparar lista de roles para re-renderizar la página con mensaje de error
        query = db.query(Role)
        total = query.count()
        per_page = 10
        pages = max(1, (total + per_page - 1) // per_page)
        page = 1
        roles = query.order_by(Role.name).offset((page - 1) * per_page).limit(per_page).all()
        roles_data = []
        for r in roles:
            perms = [rp.permission.name for rp in r.permissions if rp.permission]
            users_cnt = db.query(UserRole).filter(UserRole.role_id == r.id).count()
            roles_data.append({
                "id": r.id,
                "name": r.name,
                "permissions": ", ".join(perms),
                "users_count": users_cnt,
            })
        return TEMPLATES.TemplateResponse("roles.html", {"request": request, "roles": roles_data, "active_page": "roles", "q": "", "page": page, "pages": pages, "total": total, "per_page": per_page, "error": f"No se puede eliminar el rol '{role.name}': tiene {assigned_count} usuarios asignados"}, status_code=400)

    try:
        role_name = role.name
        db.delete(role)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='role.delete', category='roles', resource_type='role', resource_id=str(role_id), mensaje_es=f"{actor_username} eliminó el rol {role_name}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})

    return RedirectResponse(url="/roles", status_code=303)


# ============================================================================
# RUTAS DE GESTIÓN DE PERMISOS
# ============================================================================


@app.get("/permisos", response_class=HTMLResponse)
def permisos_page(
    request: Request,
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db=Depends(get_db),
    permission_ok: bool = Depends(require_permission('roles.view')),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    query = db.query(Permission)
    if q:
        like_q = f"%{q}%"
        query = query.filter(Permission.name.ilike(like_q))

    total = query.count()
    per_page = 10
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    perms = query.order_by(Permission.name).offset((page - 1) * per_page).limit(per_page).all()
    perms_data = []
    for p in perms:
        perms_data.append({"id": p.id, "name": p.name, "description": p.description or ""})

    # --- datos adicionales para la matriz integrada en la misma página ---
    roles = db.query(Role).order_by(Role.name).all()
    permissions_matrix = db.query(Permission).order_by(Permission.name).all()
    assigned = set()
    for rp in db.query(RolePermission).all():
        if rp.role_id and rp.permission_id:
            assigned.add((rp.role_id, rp.permission_id))

    return TEMPLATES.TemplateResponse(
        "permisos.html",
        {
            "request": request,
            "permissions": perms_data,
            "active_page": "permisos",
            "q": q or "",
            "page": page,
            "pages": pages,
            "total": total,
            "per_page": per_page,
            "roles": roles,
            "permissions_matrix": permissions_matrix,
            "assigned": assigned,
        },
    )


@app.get("/permisos/export")
def permisos_export(q: Optional[str] = Query(None), db=Depends(get_db), current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    if not _require_admin(current_user, db) and not has_permission(db, current_user.get('user_id'), 'roles.view'):
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado"})

    query = db.query(Permission).order_by(Permission.name)
    if q:
        like_q = f"%{q}%"
        query = query.filter(Permission.name.ilike(like_q))

    perms = query.all()

    # build CSV
    import csv, io
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["name", "description"])
    for p in perms:
        writer.writerow([p.name, p.description or ""])

    csv_data = out.getvalue()
    out.close()

    headers = {
        "Content-Disposition": "attachment; filename=permissions.csv",
        "Content-Type": "text/csv; charset=utf-8",
    }
    return Response(content=csv_data, headers=headers, media_type="text/csv")


@app.get("/permisos/create", response_class=HTMLResponse)
def permisos_create_page(request: Request, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return TEMPLATES.TemplateResponse("permiso_form.html", {"request": request, "action": "create", "perm": None})


@app.post("/permisos/create", response_class=HTMLResponse)
def permisos_create_submit(request: Request, background_tasks: BackgroundTasks, name: str = Form(...), description: Optional[str] = Form(""), db=Depends(get_db), current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    try:
        perm = Permission(name=name, description=description)
        db.add(perm)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='permission.create', category='permissions', resource_type='permission', resource_id=str(perm.id), mensaje_es=f"{actor_username} creó el permiso {name}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("permiso_form.html", {"request": request, "action": "create", "error": str(e), "perm": {"name": name, "description": description}}, status_code=400)

    return RedirectResponse(url="/permisos", status_code=303)


@app.get("/permisos/{perm_id}/edit", response_class=HTMLResponse)
def permisos_edit_page(request: Request, perm_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    perm = db.query(Permission).filter(Permission.id == perm_id).first()
    if not perm:
        return RedirectResponse(url="/permisos", status_code=303)
    return TEMPLATES.TemplateResponse("permiso_form.html", {"request": request, "action": "edit", "perm": {"id": perm.id, "name": perm.name, "description": perm.description}})


@app.post("/permisos/{perm_id}/edit", response_class=HTMLResponse)
def permisos_edit_submit(request: Request, background_tasks: BackgroundTasks, perm_id: int, name: str = Form(...), description: Optional[str] = Form(""), db=Depends(get_db), current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    perm = db.query(Permission).filter(Permission.id == perm_id).first()
    if not perm:
        return RedirectResponse(url="/permisos", status_code=303)

    try:
        perm.name = name
        perm.description = description
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='permission.update', category='permissions', resource_type='permission', resource_id=str(perm.id), mensaje_es=f"{actor_username} actualizó el permiso {name}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("permiso_form.html", {"request": request, "action": "edit", "error": str(e), "perm": {"id": perm.id, "name": name, "description": description}}, status_code=400)

    return RedirectResponse(url="/permisos", status_code=303)


@app.post("/permisos/{perm_id}/delete")
def permisos_delete(request: Request, background_tasks: BackgroundTasks, perm_id: int, current_user: Optional[dict] = Depends(get_current_user), db=Depends(get_db), permission_ok: bool = Depends(require_permission('roles.manage'))):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if not _require_admin(current_user, db):
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado"})

    perm = db.query(Permission).filter(Permission.id == perm_id).first()
    if not perm:
        return JSONResponse(status_code=404, content={"detail": "Permiso no encontrado"})

    try:
        perm_name = perm.name
        db.delete(perm)
        db.commit()
        try:
            actor_id = current_user.get("user_id") if current_user else None
            actor_username = current_user.get("sub") if current_user else None
            if background_tasks is not None:
                _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='permission.delete', category='permissions', resource_type='permission', resource_id=str(perm_id), mensaje_es=f"{actor_username} eliminó el permiso {perm_name}")
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})

    return RedirectResponse(url="/permisos", status_code=303)


# =====================
# MATRIZ DE PERMISOS (UI)
# =====================


@app.get("/permisos/matriz", response_class=HTMLResponse)
def permisos_matriz_page(
    request: Request,
    role_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
    permission_ok: bool = Depends(require_permission('roles.view')),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Solo admin o roles con vista pueden acceder
    if not _require_admin(current_user, db) and not has_permission(db, current_user.get('user_id'), 'roles.view'):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    # lista completa para el select de filtro
    roles_all = db.query(Role).order_by(Role.name).all()
    # columnas: todos o solo el rol seleccionado
    if role_id:
        roles = db.query(Role).filter(Role.id == role_id).order_by(Role.name).all()
    else:
        roles = roles_all

    # permisos; aplicar búsqueda si se provee q
    perms_q = db.query(Permission).order_by(Permission.name)
    if q:
        like_q = f"%{q}%"
        perms_q = perms_q.filter((Permission.name.ilike(like_q)) | (Permission.description.ilike(like_q)))
    permissions = perms_q.all()

    # Construir conjunto de asignaciones para la UI
    assigned = set()
    for rp in db.query(RolePermission).all():
        if rp.role_id and rp.permission_id:
            assigned.add((rp.role_id, rp.permission_id))

    return TEMPLATES.TemplateResponse(
        "permission_matrix.html",
        {
            "request": request,
            "roles": roles,
            "roles_all": roles_all,
            "permissions": permissions,
            "assigned": assigned,
            "active_page": "permisos",
            "role_id": role_id,
            "q": q,
        },
    )


@app.post("/permisos/matriz/guardar", response_class=HTMLResponse)
async def permisos_matriz_guardar(request: Request, background_tasks: BackgroundTasks, db=Depends(get_db), current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Solo admin puede modificar asignaciones
    if not _require_admin(current_user, db):
        return TEMPLATES.TemplateResponse("dashboard.html", {"request": request, "error": "Acceso denegado"}, status_code=403)

    form = await request.form()
    formdata = dict(form)

    # Leer todos roles y permisos
    roles = db.query(Role).all()
    perms = db.query(Permission).all()

    # Para cada combinación, comprobar si checkbox presente
    new_assignments = set()
    for r in roles:
        for p in perms:
            key = f"assign_{r.id}_{p.id}"
            if key in formdata:
                new_assignments.add((r.id, p.id))

    # Borrar todas las asignaciones y reinsertar según nuevo conjunto (sencillo y seguro)
    try:
        db.query(RolePermission).delete()
        db.commit()
        for (rid, pid) in new_assignments:
            db.add(RolePermission(role_id=rid, permission_id=pid))
        db.commit()
    except Exception as e:
        db.rollback()
        return TEMPLATES.TemplateResponse("permission_matrix.html", {"request": request, "roles": roles, "permissions": perms, "assigned": new_assignments, "error": str(e)})

    try:
        actor_id = current_user.get("user_id") if current_user else None
        actor_username = current_user.get("sub") if current_user else None
        if background_tasks is not None:
            _enqueue_with_request(background_tasks, request, actor_id=actor_id, actor_username=actor_username, action='permission.matrix.update', category='permissions', resource_type='matrix', resource_id='', mensaje_es=f"{actor_username} actualizó la matriz de permisos")
    except Exception:
        pass

    return RedirectResponse(url="/permisos/matriz", status_code=303)


@app.get("/permisos/matriz/export")
def permisos_matriz_export(
    role_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # Solo admin o roles con vista pueden exportar
    if not _require_admin(current_user, db) and not has_permission(db, current_user.get('user_id'), 'roles.view'):
        return JSONResponse(status_code=403, content={"detail": "Acceso denegado"})

    # roles para cabecera
    roles_q = db.query(Role).order_by(Role.name)
    if role_id:
        roles_q = roles_q.filter(Role.id == role_id)
    roles = roles_q.all()

    # permisos
    perms_q = db.query(Permission).order_by(Permission.name)
    if q:
        like_q = f"%{q}%"
        perms_q = perms_q.filter((Permission.name.ilike(like_q)) | (Permission.description.ilike(like_q)))
    permissions = perms_q.all()

    # asignaciones
    assigned = set((rp.role_id, rp.permission_id) for rp in db.query(RolePermission).all())

    # construir CSV
    import csv, io

    out = io.StringIO()
    writer = csv.writer(out)
    header = ["permission", "description"] + [r.name for r in roles]
    writer.writerow(header)

    for p in permissions:
        row = [p.name, p.description or ""]
        for r in roles:
            row.append("X" if (r.id, p.id) in assigned else "")
        writer.writerow(row)

    csv_data = out.getvalue()
    out.close()

    filename = "permission_matrix.csv"
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"",
        "Content-Type": "text/csv; charset=utf-8",
    }
    return Response(content=csv_data, headers=headers, media_type="text/csv")


@app.get("/auditoria", response_class=HTMLResponse)
def auditoria_page(
    request: Request,
    q: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    db=Depends(get_db),
    permission_ok: bool = Depends(require_permission('audit.view')),
    current_user: Optional[dict] = Depends(get_current_user),
):
    """Página de auditoría — muestra `mensaje_es` y `detalle_es` de la tabla `audit_logs`.
    Requiere permiso `audit.view`.
    """
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    per_page = 10
    params = {}
    where_clauses = ["1=1"]
    if q:
        like_q = f"%{q}%"
        params["like_q"] = like_q
        where_clauses.append("(mensaje_es LIKE :like_q OR detalle_es LIKE :like_q OR actor_username LIKE :like_q OR action LIKE :like_q)")
    if user:
        params["actor"] = user
        where_clauses.append("actor_username = :actor")
    if module:
        params["category"] = module
        where_clauses.append("category = :category")
    if date_from:
        # inclusive start
        params["date_from"] = date_from.isoformat()
        where_clauses.append("created_at >= :date_from")
    if date_to:
        # make end exclusive by adding one day
        params["date_to"] = (date_to + timedelta(days=1)).isoformat()
        where_clauses.append("created_at < :date_to")

    where_sql = " AND ".join(where_clauses)

    # Count
    count_sql = f"SELECT COUNT(*) as cnt FROM audit_logs WHERE {where_sql}"
    try:
        total_row = db.execute(text(count_sql), params).fetchone()
        total = int(total_row[0]) if total_row is not None else 0
    except Exception:
        total = 0

    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages

    offset = (page - 1) * per_page

    list_sql = (
        "SELECT id, created_at, actor_username, action, category, resource_type, resource_id, mensaje_es, detalle_es "
        f"FROM audit_logs WHERE {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    params.update({"limit": per_page, "offset": offset})

    try:
        rows = db.execute(text(list_sql), params).fetchall()
    except Exception:
        rows = []

    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "created_at": r[1],
            "actor_username": r[2],
            "action": r[3],
            "category": r[4],
            "resource_type": r[5],
            "resource_id": r[6],
            "mensaje_es": r[7],
            "detalle_es": r[8],
        })

    # Fetch filter lists for selects
    try:
        actor_rows = db.execute(text("SELECT DISTINCT actor_username FROM audit_logs WHERE actor_username IS NOT NULL ORDER BY actor_username")).fetchall()
        actors = [a[0] for a in actor_rows if a[0]]
    except Exception:
        actors = []
    try:
        cat_rows = db.execute(text("SELECT DISTINCT category FROM audit_logs WHERE category IS NOT NULL ORDER BY category")).fetchall()
        modules = [c[0] for c in cat_rows if c[0]]
    except Exception:
        modules = []

    return TEMPLATES.TemplateResponse(
        "auditoria.html",
        {
            "request": request,
            "active_page": "auditoria",
            "logs": items,
            "per_page": per_page,
            "q": q or "",
            "user": user or "",
            "module": module or "",
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "actors": actors,
            "modules": modules,
            "page": page,
            "pages": pages,
            "total": total,
        },
    )


@app.get("/auditoria/export")
def auditoria_export(
    request: Request,
    q: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db=Depends(get_db),
    permission_ok: bool = Depends(require_permission('audit.view')),
    current_user: Optional[dict] = Depends(get_current_user),
):
    params = {}
    where_clauses = ["1=1"]
    if q:
        like_q = f"%{q}%"
        params["like_q"] = like_q
        where_clauses.append("(mensaje_es LIKE :like_q OR detalle_es LIKE :like_q OR actor_username LIKE :like_q OR action LIKE :like_q)")
    if user:
        params["actor"] = user
        where_clauses.append("actor_username = :actor")
    if module:
        params["category"] = module
        where_clauses.append("category = :category")
    # Parse optional date strings (accept empty strings without failing)
    parsed_from = None
    parsed_to = None
    if date_from:
        try:
            parsed_from = date.fromisoformat(date_from)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato inválido para 'date_from'. Use YYYY-MM-DD")
    if date_to:
        try:
            parsed_to = date.fromisoformat(date_to)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato inválido para 'date_to'. Use YYYY-MM-DD")

    if parsed_from:
        params["date_from"] = parsed_from.isoformat()
        where_clauses.append("created_at >= :date_from")
    if parsed_to:
        params["date_to"] = (parsed_to + timedelta(days=1)).isoformat()
        where_clauses.append("created_at < :date_to")

    where_sql = " AND ".join(where_clauses)
    sql = f"SELECT uuid, actor_id, actor_username, action, category, resource_type, resource_id, ip_address, user_agent, request_id, duration_ms, mensaje_es, detalle_es, created_at FROM audit_logs WHERE {where_sql} ORDER BY created_at DESC"

    try:
        rs = db.execute(text(sql), params)
    except Exception as exc:
        try:
            logger.exception("Error consultando logs: %s", exc)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error consultando logs: {str(exc)}")

    def _iter_rows():
        import csv
        from io import StringIO

        buf = StringIO()
        writer = csv.writer(buf)
        # header
        writer.writerow(["uuid","actor_id","actor_username","action","category","resource_type","resource_id","ip_address","user_agent","request_id","duration_ms","mensaje_es","detalle_es","created_at"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for row in rs:
            values = [str(row[0] or ''), str(row[1] or ''), str(row[2] or ''), str(row[3] or ''), str(row[4] or ''), str(row[5] or ''), str(row[6] or ''), str(row[7] or ''), str(row[8] or ''), str(row[9] or ''), str(row[10] or ''), str(row[11] or ''), str(row[12] or ''), str(row[13] or '')]
            writer.writerow(values)
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(_iter_rows(), media_type='text/csv', headers={"Content-Disposition": "attachment; filename=auditoria_export.csv"})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    # Verificar autenticación
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # Estadísticas para el dashboard
    total_entidades = db.query(Entity).count()
    total_archivos = db.query(FileModel).count()
    total_hechos = db.query(Fact).count()
    # Archivos recientes: traer objetos File con entidad y periodo
    recent_files = (
        db.query(FileModel)
        .options()
        .outerjoin(Entity)
        .outerjoin(Period)
        .order_by(FileModel.created_at.desc())
        .limit(5)
        .all()
    )

    archivos_recientes = []
    # Para evitar N+1, precompute counts per file id
    file_ids = [f.id for f in recent_files]
    facts_counts = {}
    if file_ids:
        rows = db.query(Fact.file_id, func.count(Fact.id)).filter(Fact.file_id.in_(file_ids)).group_by(Fact.file_id).all()
        facts_counts = {r[0]: r[1] for r in rows}

    for f in recent_files:
        periodo = _format_period(getattr(f.period, 'start', None), getattr(f.period, 'end', None))
        archivos_recientes.append({
            "filename": f.filename,
            "entidad": f.entity.name if f.entity else "N/A",
            "periodo": periodo,
            "taxonomy": f.taxonomy,
            "total_hechos": int(facts_counts.get(f.id, 0)),
            "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "N/A",
        })

    # Alertas activas: contar archivos con warnings no nulos
    alertas_activas = db.query(FileModel).filter(FileModel.warnings != None).count()

    # Nuevas entidades (últimos 30 días)
    from datetime import datetime, timedelta
    dias_nuevas = 30
    desde = datetime.utcnow() - timedelta(days=dias_nuevas)
    nuevas_entidades = db.query(Entity).filter(Entity.created_at >= desde).count()

    stats = {
        "total_entidades": total_entidades,
        "total_archivos": total_archivos,
        "total_hechos": total_hechos,
        "alertas_activas": alertas_activas,
        "nuevas_entidades": nuevas_entidades,
    }

    # Archivos por mes: últimos 12 meses relativos (evita dependencias de funciones DB)
    from datetime import datetime
    now = datetime.utcnow()
    archivos_por_mes = []
    archivos_month_labels = []
    # helper to get first day of month
    def _first_of_month(y, m):
        return datetime(y, m, 1)

    def _add_month(y, m, delta):
        # add delta months to year/month
        total = y * 12 + (m - 1) + delta
        ny = total // 12
        nm = (total % 12) + 1
        return ny, nm

    # Build months from oldest to newest (11 months ago .. current)
    for i in range(11, -1, -1):
        y, mo = _add_month(now.year, now.month, -i)
        start = _first_of_month(y, mo)
        ny, nm = _add_month(y, mo, 1)
        end = _first_of_month(ny, nm)
        try:
            cnt = db.query(FileModel).filter(FileModel.created_at >= start, FileModel.created_at < end).count()
        except Exception:
            cnt = 0
        archivos_por_mes.append(int(cnt))
        # etiquetas en español abreviadas y año corto (p.ej. Dic/24)
        meses_es = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        year_short = str(y)[2:]
        archivos_month_labels.append(f"{meses_es[mo - 1]}/{year_short}")

    # Distribución de entidades por sector (top 5)
    sectores_labels = []
    sectores_data = []
    try:
        # Usar COALESCE para agrupar valores NULL como 'Sin sector'
        sec_label = func.coalesce(Entity.sector, 'Sin sector')
        sec_rows = (
            db.query(sec_label.label('sector'), func.count(Entity.id))
            .group_by(sec_label)
            .order_by(func.count(Entity.id).desc())
            .limit(5)
            .all()
        )
        for s in sec_rows:
            sectores_labels.append(s[0])
            sectores_data.append(int(s[1]))
    except Exception:
        # fallback: some default
        sectores_labels = ["Bancos", "Seguros", "Otros"]
        sectores_data = [40, 35, 25]

    response = TEMPLATES.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "stats": stats,
            "archivos_recientes": archivos_recientes,
                "archivos_por_mes": archivos_por_mes,
                "archivos_month_labels": archivos_month_labels,
                "sectores_labels": sectores_labels,
                "sectores_data": sectores_data,
        },
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user)
) -> HTMLResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    response = TEMPLATES.TemplateResponse(
        "upload.html",
        {"request": request, "active_page": "upload"},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/entidades", response_class=HTMLResponse)
def entidades_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    entities = db.query(Entity).order_by(Entity.name).all()
    response = TEMPLATES.TemplateResponse(
        "entidades.html",
        {"request": request, "active_page": "entidades", "entities": entities},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/archivos", response_class=HTMLResponse)
def archivos_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    archivos = (
        db.query(FileModel)
        .options(joinedload(FileModel.entity))
        .order_by(FileModel.created_at.desc())
        .all()
    )
    response = TEMPLATES.TemplateResponse(
        "archivos.html",
        {"request": request, "active_page": "archivos", "archivos": archivos},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/comparativos", response_class=HTMLResponse)
def comparativos(
    request: Request,
    entidad: Optional[str] = Query(None),
    concepto: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
) -> HTMLResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    rows = _fetch_comparativos_rows(db, entidad, concepto, period_start, period_end)
    response = TEMPLATES.TemplateResponse(
        "comparativos.html",
        {"request": request, "rows": rows, "active_page": "comparativos"},
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _render_export_pdf(rows: List[dict]) -> bytes:
    html_str = TEMPLATES.get_template("comparativos_pdf.html").render(
        rows=rows,
        today=date.today(),
    )
    pdf_content: Optional[bytes] = None
    try:
        config = get_pdfkit_config()
        pdf_content = pdfkit.from_string(html_str, False, configuration=config, options=PDF_OPTIONS)
    except Exception:
        pdf_content = None

    if pdf_content is None:
        out = io.BytesIO()
        pisa.CreatePDF(io.StringIO(html_str), dest=out)
        pdf_content = out.getvalue()
    return pdf_content


@app.get("/export/csv")
def export_csv(
    entidad: Optional[str] = Query(None),
    concepto: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
) -> StreamingResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    rows = _fetch_comparativos_rows(db, entidad, concepto, period_start, period_end)
    df = _rows_to_dataframe(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    filename = "comparativos.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export/xlsx")
def export_xlsx(
    entidad: Optional[str] = Query(None),
    concepto: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
) -> StreamingResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    rows = _fetch_comparativos_rows(db, entidad, concepto, period_start, period_end)
    df = _rows_to_dataframe(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="comparativos")
    buf.seek(0)
    filename = "comparativos.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/export/pdf")
def export_pdf(
    entidad: Optional[str] = Query(None),
    concepto: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db),
) -> StreamingResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    rows = _fetch_comparativos_rows(db, entidad, concepto, period_start, period_end)
    content = _render_export_pdf(rows)
    buf = io.BytesIO(content)
    filename = "comparativos.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/upload-xbrl", response_model=FileResponse)
def upload_xbrl(
    request: Request,
    xbrl: UploadFile = File(...),
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> FileResponse:
    if not current_user:
        response = RedirectResponse(url="/login", status_code=303)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(xbrl.filename).suffix) as tmp:
            tmp.write(xbrl.file.read())
            tmp_path = Path(tmp.name)

        try:
            parsed = parse_xbrl(tmp_path)
        except Exception as exc:  # pragma: no cover - defensive
            tmp_path.unlink(missing_ok=True)
            logger.exception("Error leyendo XBRL")
            if request.headers.get("HX-Request"):
                return HTMLResponse(f"Error leyendo XBRL: {exc}")
            raise HTTPException(status_code=400, detail=f"Error leyendo XBRL: {exc}")

        # Guardar una copia del archivo XBRL en la carpeta `uploads/` del proyecto
        stored_path = None
        try:
            uploads_dir = BASE_DIR.parent / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            dest_name = f"{uuid.uuid4().hex}_{Path(xbrl.filename).name}"
            dest_path = uploads_dir / dest_name
            shutil.copy(str(tmp_path), str(dest_path))
            stored_path = str(dest_path)
        except Exception:
            # No impedir la ingestión si falla el guardado físico; registrar y continuar
            logger.exception("No se pudo guardar copia del XBRL en uploads/")

        tmp_path.unlink(missing_ok=True)

        facts = parsed.get("facts", [])
        if not facts:
            msg = "El archivo no contiene hechos válidos"
            if request.headers.get("HX-Request"):
                return HTMLResponse(msg)
            raise HTTPException(status_code=400, detail=msg)

        first_fact = facts[0]
        ident = first_fact.get("entity_identifier") or {}
        entity_nit = ident.get("identifier")
        entity_name = entity_nit or "desconocido"
        entity = db.query(Entity).filter(Entity.nit == entity_nit).first() if entity_nit else None
        if not entity:
            entity = Entity(name=entity_name, nit=entity_nit)
            db.add(entity)
            db.flush()

        period_start = first_fact.get("period_start")
        period_end = first_fact.get("period_end")
        period_obj = None
        if period_start and period_end:
            period_obj = (
                db.query(Period)
                .filter(Period.start == period_start, Period.end == period_end)
                .first()
            )
            if not period_obj:
                period_obj = Period(start=period_start, end=period_end, frequency=None)
                db.add(period_obj)
                db.flush()

        currency = first_fact.get("currency")
        file_row = FileModel(
            filename=xbrl.filename,
            taxonomy=parsed.get("taxonomy"),
            version=parsed.get("version"),
            currency=currency,
            entity_id=entity.id,
            period_id=period_obj.id if period_obj else None,
            warnings={"stored_path": stored_path} if stored_path else None,
        )
        db.add(file_row)
        db.flush()

        fact_rows = []
        for fact in facts:
            try:
                numeric_val = float(fact.get("value")) if fact.get("value") not in (None, "") else None
            except Exception:
                numeric_val = None
            canonical = resolve_canonical_concept(fact.get("concept_qname"))
            fact_rows.append(
                Fact(
                    file_id=file_row.id,
                    concept_qname=fact.get("concept_qname"),
                    canonical_concept=canonical,
                    value=numeric_val,
                    decimals=fact.get("decimals"),
                    unit=fact.get("unit"),
                    currency=fact.get("currency"),
                    dimensions=fact.get("dimensions"),
                )
            )

        db.add_all(fact_rows)
        db.commit()
        db.refresh(file_row)

        periodo_str = _format_period(period_start, period_end)

        if request.headers.get("HX-Request"):
            return HTMLResponse(
                f"<div><strong>Archivo:</strong> {file_row.filename}<br>"
                f"<strong>Entidad:</strong> {entity.name or ''} ({entity.nit or 'N/A'})<br>"
                f"<strong>Período:</strong> {periodo_str}<br>"
                f"<strong>Taxonomía:</strong> {file_row.taxonomy or 'N/A'}<br>"
                f"<strong>Versión:</strong> {file_row.version or 'N/A'}<br>"
                f"<strong>Moneda:</strong> {file_row.currency or 'N/A'}<br>"
                f"<strong>Hechos:</strong> {len(fact_rows)}</div>"
            )

        return file_row
    except HTTPException as http_exc:
        if request.headers.get("HX-Request"):
            return HTMLResponse(str(http_exc.detail))
        raise


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ==============================
# RUTAS: Entidades (Catálogo)
# ==============================


@app.get("/entidades", response_class=HTMLResponse)
def entidades_page(
    request: Request,
    q: Optional[str] = Query(None),
    active: Optional[str] = Query(None),
    page: int = Query(1),
    per_page: int = Query(20),
    db = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user),
    permission_ok: bool = Depends(require_permission('entities.view')),
):
    query = db.query(Entity)
    if q:
        likeq = f"%{q}%"
        query = query.filter((Entity.name.ilike(likeq)) | (Entity.nit.ilike(likeq)))
    if active is not None:
        if active in ("1", "true", "True"):
            query = query.filter(Entity.is_active == True)
        elif active in ("0", "false", "False"):
            query = query.filter(Entity.is_active == False)

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    entities = query.order_by(Entity.name).offset((page - 1) * per_page).limit(per_page).all()

    return TEMPLATES.TemplateResponse("entidades.html", {
        "request": request,
        "entities": entities,
        "q": q,
        "active": active,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "total": total,
        "active_page": "entidades",
    })


@app.get("/entidades/create", response_class=HTMLResponse)
def entidades_create_page(request: Request, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    return TEMPLATES.TemplateResponse("entity_form.html", {"request": request, "entity": None, "active_page": "entidades", "error": None})


@app.post("/entidades/create")
def entidades_create(
    request: Request,
    name: str = Form(...),
    nit: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    entity_type: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    delegatura: Optional[str] = Form(None),
    short_name: Optional[str] = Form(None),
    is_active: Optional[str] = Form("1"),
    db = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    current_user: Optional[dict] = Depends(get_current_user),
    permission_ok: bool = Depends(require_permission('entities.manage')),
):
    ent = Entity(
        name=name,
        nit=nit or None,
        sector=sector,
        entity_type=entity_type,
        code=code,
        delegatura=delegatura,
        short_name=short_name,
        is_active=(is_active not in ("0", "false", "False")),
    )
    db.add(ent)
    try:
        db.commit()
        db.refresh(ent)
    except IntegrityError as ie:
        db.rollback()
        # Mostrar el formulario con error
        return TEMPLATES.TemplateResponse("entity_form.html", {"request": request, "entity": ent, "active_page": "entidades", "error": "El NIT ya existe en otra entidad."})
    try:
        if background_tasks is not None:
            _enqueue_with_request(background_tasks, request, actor_id=current_user.get("user_id"), action='entities.create', category='xbrl', resource_type='entity', resource_id=str(ent.id), mensaje_es=f"Entidad {ent.name} creada")
    except Exception:
        pass
    return RedirectResponse(url="/entidades", status_code=303)


@app.get("/entidades/{entity_id}/edit", response_class=HTMLResponse)
def entidades_edit_page(entity_id: int, request: Request, db = Depends(get_db), current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        return RedirectResponse(url="/entidades", status_code=303)
    return TEMPLATES.TemplateResponse("entity_form.html", {"request": request, "entity": ent, "active_page": "entidades", "error": None})


@app.post("/entidades/{entity_id}/edit")
def entidades_edit(entity_id: int,
                   name: str = Form(...),
                   nit: Optional[str] = Form(None),
                   sector: Optional[str] = Form(None),
                   entity_type: Optional[str] = Form(None),
                   code: Optional[str] = Form(None),
                   delegatura: Optional[str] = Form(None),
                   short_name: Optional[str] = Form(None),
                   is_active: Optional[str] = Form("1"),
                   db = Depends(get_db),
                   background_tasks: BackgroundTasks = None,
                   current_user: Optional[dict] = Depends(get_current_user),
                   permission_ok: bool = Depends(require_permission('entities.manage'))):
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    ent.name = name
    ent.nit = nit or None
    ent.sector = sector
    ent.entity_type = entity_type
    ent.code = code
    ent.delegatura = delegatura
    ent.short_name = short_name
    ent.is_active = (is_active not in ("0", "false", "False"))
    db.add(ent)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return TEMPLATES.TemplateResponse("entity_form.html", {"request": request, "entity": ent, "active_page": "entidades", "error": "El NIT ya existe en otra entidad."})
    try:
        if background_tasks is not None:
            _enqueue_with_request(background_tasks, None, actor_id=current_user.get("user_id"), action='entities.update', category='xbrl', resource_type='entity', resource_id=str(ent.id), mensaje_es=f"Entidad {ent.name} actualizada")
    except Exception:
        pass
    return RedirectResponse(url="/entidades", status_code=303)


@app.post("/entidades/{entity_id}/toggle")
def entidades_toggle(entity_id: int, db = Depends(get_db), background_tasks: BackgroundTasks = None, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    ent.is_active = not bool(ent.is_active)
    db.add(ent)
    db.commit()
    try:
        if background_tasks is not None:
            _enqueue_with_request(background_tasks, None, actor_id=current_user.get("user_id"), action='entities.toggle', category='xbrl', resource_type='entity', resource_id=str(ent.id), mensaje_es=f"Entidad {ent.name} {'activada' if ent.is_active else 'desactivada'}")
    except Exception:
        pass
    return RedirectResponse(url="/entidades", status_code=303)


@app.post("/entidades/{entity_id}/delete")
def entidades_delete(entity_id: int, db = Depends(get_db), background_tasks: BackgroundTasks = None, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    """No borra la fila; marca la entidad como inactiva (soft-delete funcional)."""
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    ent.is_active = False
    db.add(ent)
    db.commit()
    try:
        if background_tasks is not None:
            _enqueue_with_request(background_tasks, None, actor_id=current_user.get("user_id"), action='entities.delete', category='xbrl', resource_type='entity', resource_id=str(ent.id), mensaje_es=f"Entidad {ent.name} inactivada")
    except Exception:
        pass
    return RedirectResponse(url="/entidades", status_code=303)


@app.post("/entidades/import")
def entidades_import(file: UploadFile = File(...), db = Depends(get_db), background_tasks: BackgroundTasks = None, current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    # soporta CSV y Excel
    try:
        content = file.file.read()
        file.file.seek(0)
        if file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls'):
            df = pd.read_excel(file.file)
        else:
            df = pd.read_csv(io.BytesIO(content))
        created = 0
        updated = 0
        for _, row in df.iterrows():
            nit = str(row.get('nit') or row.get('NIT') or '')
            name = str(row.get('name') or row.get('nombre') or '')
            sector = row.get('sector')
            typev = row.get('type') or row.get('tipo')
            if not name:
                continue
            ent = None
            if nit:
                ent = db.query(Entity).filter(Entity.nit == nit).first()
            if not ent:
                ent = Entity(name=name, nit=nit or None, sector=sector, type=typev)
                db.add(ent)
                created += 1
            else:
                ent.name = name
                ent.sector = sector
                ent.type = typev
                updated += 1
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error importando: {e}")
    return RedirectResponse(url="/entidades", status_code=303)


@app.get("/entidades/export")
def entidades_export(q: Optional[str] = Query(None), db = Depends(get_db), current_user: Optional[dict] = Depends(get_current_user), permission_ok: bool = Depends(require_permission('entities.manage'))):
    query = db.query(Entity)
    if q:
        likeq = f"%{q}%"
        query = query.filter((Entity.name.ilike(likeq)) | (Entity.nit.ilike(likeq)))
    rows = query.order_by(Entity.name).all()
    import csv
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['id','nit','name','sector','type','is_active','created_at','updated_at'])
    for e in rows:
        writer.writerow([e.id, e.nit or '', e.name or '', e.sector or '', e.type or '', '1' if e.is_active else '0', e.created_at or '', e.updated_at or ''])
    si.seek(0)
    return StreamingResponse(io.BytesIO(si.getvalue().encode('utf-8')), media_type='text/csv', headers={"Content-Disposition": "attachment; filename=entidades.csv"})
