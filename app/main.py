from __future__ import annotations

import io
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

import pandas as pd
import pdfkit
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from xhtml2pdf import pisa

from .auth import authenticate_user, create_access_token, decode_token, change_password, validate_password_strength
from .canonical_mapping import resolve_canonical_concept
from .db import SessionLocal, engine
from .ingest_arelle import parse_xbrl
from .logger import get_logger, setup_application_logging
from .models import Base, Entity, File as FileModel, Fact, Period
from .pdf_config import PDF_OPTIONS, get_pdfkit_config
from .schemas import FileResponse

# Setup application logging
logger = setup_application_logging()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Corvus International Group")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Muestra la página de login"""
    return TEMPLATES.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db = Depends(get_db)
):
    """Procesa el login del usuario y genera token JWT"""
    
    # Autenticar usuario
    user = authenticate_user(db, username, password)
    
    if not user:
        logger.warning(f"Intento de login fallido para usuario: {username}")
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
    
    # Redirigir al dashboard con el token en cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutos
        samesite="lax"
    )
    
    return response


@app.get("/logout")
async def logout(request: Request):
    """Cierra la sesión del usuario eliminando el token"""
    logger.info("Usuario cerró sesión")
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
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
        return RedirectResponse(url="/login", status_code=303)
    
    return TEMPLATES.TemplateResponse("change_password.html", {
        "request": request,
        "error": error,
        "success": success
    })


@app.post("/change-password", response_class=HTMLResponse)
async def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user),
    db = Depends(get_db)
):
    """Procesa el cambio de contraseña"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Validar que las nuevas contraseñas coincidan
    if new_password != confirm_password:
        return TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": "Las contraseñas nuevas no coinciden"
        }, status_code=400)
    
    # Validar fortaleza de la contraseña
    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        return TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": message
        }, status_code=400)
    
    # Cambiar contraseña
    user_id = current_user.get("user_id")
    success = change_password(db, user_id, current_password, new_password)
    
    if success:
        logger.info(f"Contraseña cambiada para usuario ID: {user_id}")
        return TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "success": "Contraseña cambiada exitosamente"
        })
    else:
        return TEMPLATES.TemplateResponse("change_password.html", {
            "request": request,
            "error": "Contraseña actual incorrecta"
        }, status_code=400)


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
        return RedirectResponse(url="/login", status_code=303)
    
    # Estadísticas para el dashboard
    total_entidades = db.query(Entity).count()
    total_archivos = db.query(FileModel).count()
    total_hechos = db.query(Fact).count()
    
    # Archivos recientes
    archivos_recientes_query = (
        db.query(
            FileModel.filename,
            FileModel.taxonomy,
            FileModel.created_at,
            Entity.name.label("entidad"),
            Period.start.label("period_start"),
            Period.end.label("period_end"),
        )
        .outerjoin(Entity, FileModel.entity)
        .outerjoin(Period, FileModel.period)
        .order_by(FileModel.created_at.desc())
        .limit(5)
        .all()
    )
    
    archivos_recientes = []
    for archivo in archivos_recientes_query:
        periodo = _format_period(archivo.period_start, archivo.period_end)
        # Contar hechos por archivo
        total_hechos_archivo = db.query(Fact).filter(Fact.file_id == FileModel.id).count() if hasattr(archivo, 'id') else 0
        archivos_recientes.append({
            "filename": archivo.filename,
            "entidad": archivo.entidad or "N/A",
            "periodo": periodo,
            "taxonomy": archivo.taxonomy,
            "total_hechos": total_hechos_archivo,
            "created_at": archivo.created_at.strftime("%Y-%m-%d %H:%M") if archivo.created_at else "N/A",
        })
    
    stats = {
        "total_entidades": total_entidades,
        "total_archivos": total_archivos,
        "total_hechos": total_hechos,
        "alertas_activas": 0,
        "nuevas_entidades": 0,
        "archivos_mes": 0,
    }
    
    return TEMPLATES.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "stats": stats,
            "archivos_recientes": archivos_recientes,
            "archivos_por_mes": [0] * 12,
            "sectores_labels": ["Bancos", "Seguros", "Otros"],
            "sectores_data": [40, 35, 25],
        },
    )


@app.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user)
) -> HTMLResponse:
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    return TEMPLATES.TemplateResponse(
        "upload.html",
        {"request": request, "active_page": "upload"},
    )


@app.get("/entidades", response_class=HTMLResponse)
def entidades_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    entities = db.query(Entity).order_by(Entity.name).all()
    return TEMPLATES.TemplateResponse(
        "entidades.html",
        {"request": request, "active_page": "entidades", "entities": entities},
    )


@app.get("/archivos", response_class=HTMLResponse)
def archivos_page(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user),
    db=Depends(get_db)
) -> HTMLResponse:
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    archivos = (
        db.query(FileModel)
        .options(joinedload(FileModel.entity))
        .order_by(FileModel.created_at.desc())
        .all()
    )
    return TEMPLATES.TemplateResponse(
        "archivos.html",
        {"request": request, "active_page": "archivos", "archivos": archivos},
    )


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
        return RedirectResponse(url="/login", status_code=303)
    
    rows = _fetch_comparativos_rows(db, entidad, concepto, period_start, period_end)
    return TEMPLATES.TemplateResponse(
        "comparativos.html",
        {"request": request, "rows": rows, "active_page": "comparativos"},
    )


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
        raise HTTPException(status_code=401, detail="No autenticado")
    
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
        raise HTTPException(status_code=401, detail="No autenticado")
    
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
        raise HTTPException(status_code=401, detail="No autenticado")
    
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
        raise HTTPException(status_code=401, detail="No autenticado")
    
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
            warnings=None,
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
