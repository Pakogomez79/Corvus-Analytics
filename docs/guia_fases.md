# Guía de fases y pasos – Corvus Analytics XBRL

## 1. Preparación y entorno
- Verificar Python 3.10+ y wkhtmltopdf opcional (para pdfkit); xhtml2pdf ya es fallback.
- Crear y activar entorno virtual: `python -m venv .venv` y luego activar.
- Instalar dependencias: `pip install -r requirements.txt`.
- Configurar variables si cambian credenciales DB: `app/db.py` o via env vars (pendiente parametrización).
- MySQL: asegurar base `xbrl_analytics` creada (se crea con script actual) y usuario con permisos.

## 2. Esquema y modelos
- SQLAlchemy models: `Entity`, `Period`, `File`, `Fact`, `User`, `Role`, `UserRole` en `app/models.py`.
- Pydantic: `FileResponse`, `FactCreate`, `FileCreate` en `app/schemas.py`.
- Revisión de migraciones: Alembic aún no configurado; pendiente si se requiere versionado de schema.

## 3. Ingesta XBRL
- Endpoint `/upload-xbrl` (FastAPI): recibe archivo, usa Arelle (headless) para parsear.
- Extracción: taxonomía, versión, facts, unidades/moneda, contexto (periodos, entidad, dimensiones).
- Persistencia: crea/usa `Entity` (por identificador), `Period`, `File`, `Fact`.
- Faltante: exponer formulario en UI para subir archivos; agregar manejo de advertencias y logs.
- Faltante: mapeo canónico usando CSV de SFC (`mapping_sfc_*.csv`) para poblar `canonical_concept`.

## 4. Mapeo y normalización
- Leer CSV de mapeo por versión de taxonomía (p. ej. 220000/320000…).
- Generar diccionario concepto_origen -> concepto_canonico.
- Al crear `Fact`, completar `canonical_concept` y normalizar moneda/unidades.
- Validar periodos (instant vs duration) y frecuencia.

## 5. Comparativos y consultas
- Reemplazar datos mock en `sample_comparativos` por consultas SQL:
  - Join `File` + `Entity` + `Period` + `Fact` filtrando `canonical_concept` y periodo.
- Agregar filtros en UI (entidad, rango de fechas, conceptos).
- Export CSV/XLSX/PDF ya implementado; ajustar para usar datos reales del query.

## 6. UI y UX
- Página de inicio: agregar formulario de carga XBRL (input file, submit al endpoint) y feedback.
- Página de comparativos: tablas con filtros, paginación simple y enlaces de export.
- Mensajes de error/éxito y advertencias de validación.

## 7. Seguridad y roles (pendiente)
- Implementar auth básica (FastAPI + JWT o session) y roles (`User`, `Role`).
- Proteger endpoints de carga y export según rol.

## 8. Logging, monitoreo y manejo de errores
- Añadir logs estructurados para ingesta (éxitos/fallos, tiempo, archivo, entidad).
- Manejar errores de Arelle y DB con respuestas claras.
- Validar tamaño/tipo de archivo antes de procesar.

## 9. Pruebas
- Unitarias: funciones de mapeo y parser (con XBRL de muestra).
- Integración: llamada a `/upload-xbrl` con archivo real, verificar inserciones en MySQL.
- End-to-end manual: subir archivo, ver comparativos, exportar CSV/XLSX/PDF.

## 10. Despliegue
- Variables de entorno para credenciales DB, host/port.
- Considerar contenedorización (Dockerfile + compose con MySQL).
- Revisión de wkhtmltopdf en el entorno de despliegue o confiar en xhtml2pdf.

## 11. Lista de pendientes inmediatos
1) Exponer formulario de carga en UI y probar `/upload-xbrl` con XBRL SFC real.
2) Implementar mapeo canónico con CSV y poblar `canonical_concept`.
3) Reemplazar `sample_comparativos` por query real a DB.
4) Añadir validaciones y mensajes de feedback en la UI.
5) Configurar Alembic si se requiere versionado de schema.
