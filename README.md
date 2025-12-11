# Corvus XBRL Enterprise

Sistema empresarial para análisis de reportes financieros en formato XBRL con capacidades de comparación, indicadores financieros y generación de reportes.

## 🚀 Características Principales

- 📊 **Análisis XBRL**: Procesamiento y extracción de datos de archivos XBRL
- 🔄 **Comparativos**: Análisis multi-empresa y multi-periodo
- 📈 **Indicadores**: Cálculo automático de ratios financieros
- 📄 **Reportes**: Exportación a PDF, Excel y CSV
- 🎨 **UI Moderna**: Interfaz responsive con Corvus Design System
- 🔐 **Seguridad**: Autenticación y autorización basada en roles
- 🔔 **Alertas**: Sistema de notificaciones por umbrales financieros

## 📋 Requisitos

- Python 3.10 o superior
- MySQL 5.7+ o SQL Server 2019+
- 2GB RAM mínimo
- 500MB espacio en disco

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/Corvus-Analytics.git
cd Corvus-Analytics
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
```

### 3. Activar entorno virtual

**Windows:**
```powershell
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar variables de entorno

Copiar el archivo de ejemplo y configurar:

```bash
copy .env.example .env
```

Editar `.env` con tus configuraciones:

```env
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=xbrl_analytics
DATABASE_USER=root
DATABASE_PASSWORD=tu_password

SECRET_KEY=genera-una-clave-segura-aqui
```

### 6. Crear base de datos

**MySQL:**
```sql
CREATE DATABASE xbrl_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**SQL Server:**
```sql
CREATE DATABASE xbrl_analytics;
```

### 7. Ejecutar migraciones

```bash
alembic upgrade head
```

### 8. Ejecutar la aplicación

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La aplicación estará disponible en: `http://localhost:8000`

## 📁 Estructura del Proyecto

```
Corvus-Analytics/
├── app/
│   ├── main.py              # Aplicación FastAPI principal
│   ├── models.py            # Modelos SQLAlchemy
│   ├── db.py                # Configuración de base de datos
│   ├── schemas.py           # Esquemas Pydantic
│   ├── logger.py            # Sistema de logging
│   ├── canonical_mapping.py # Mapeo de conceptos XBRL
│   ├── ingest_arelle.py     # Procesamiento XBRL
│   ├── pdf_config.py        # Configuración PDF
│   ├── static/              # Archivos estáticos (CSS, JS)
│   └── templates/           # Plantillas HTML
├── alembic/                 # Migraciones de base de datos
├── docs/                    # Documentación
├── logs/                    # Archivos de log
├── uploads/                 # Archivos XBRL cargados
├── exports/                 # Reportes generados
├── .env                     # Variables de entorno (no incluir en git)
├── .env.example             # Ejemplo de variables de entorno
├── requirements.txt         # Dependencias Python
└── README.md               # Este archivo
```

## 🔧 Configuración Avanzada

### Logging

El sistema de logging está configurado en `app/logger.py`. Configuración disponible en `.env`:

```env
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=standard         # standard o json
LOG_MAX_BYTES=10485760      # 10MB
LOG_BACKUP_COUNT=5          # Número de archivos de respaldo
```

### Base de Datos

#### MySQL
```env
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
```

#### SQL Server
```env
DATABASE_TYPE=mssql
DATABASE_HOST=localhost
DATABASE_PORT=1433
DATABASE_DRIVER=ODBC Driver 17 for SQL Server
```

### Migraciones

Crear nueva migración:
```bash
alembic revision --autogenerate -m "Descripción del cambio"
```

Aplicar migraciones:
```bash
alembic upgrade head
```

Revertir migración:
```bash
alembic downgrade -1
```

Ver historial:
```bash
alembic history
```

## 🧪 Testing

Ejecutar tests:
```bash
pytest
```

Con cobertura:
```bash
pytest --cov=app --cov-report=html
```

## 📝 Uso Básico

### 1. Cargar archivo XBRL

```python
# Subir archivo a través de la interfaz web
# O usar la API:
POST /upload
Content-Type: multipart/form-data
file: archivo.xbrl
```

### 2. Ver entidades disponibles

```python
GET /entities
```

### 3. Generar comparativo

```python
GET /comparativos?entity_ids=1,2&period_id=1
```

### 4. Exportar a PDF

```python
GET /comparativos/pdf?entity_ids=1,2&period_id=1
```

## 🔐 Seguridad

- **Autenticación JWT**: Tokens seguros para sesiones
- **Hashing de contraseñas**: Bcrypt para almacenamiento seguro
- **Variables de entorno**: Credenciales fuera del código
- **SQL Injection**: Protección mediante ORM SQLAlchemy
- **CORS**: Configuración de orígenes permitidos

## 📚 Documentación API

La documentación interactiva de la API está disponible en:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add: nueva característica'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto es privado y propietario.

## 👥 Equipo

- **Desarrollador Principal**: Tu Nombre
- **Organización**: Tu Empresa

## 📞 Soporte

Para soporte técnico o consultas:
- Email: soporte@tu-empresa.com
- Issues: [GitHub Issues](https://github.com/tu-usuario/Corvus-Analytics/issues)

## 🗺️ Roadmap

- [x] Infraestructura base
- [x] Procesamiento XBRL
- [x] Sistema de logging
- [x] Migraciones de BD
- [ ] Autenticación JWT
- [ ] Gestión de usuarios y roles
- [ ] Dashboard interactivo
- [ ] Sistema de alertas
- [ ] Análisis predictivo

## 📊 Estado del Proyecto

**Versión actual**: 1.0.0  
**Estado**: En desarrollo activo  
**Última actualización**: Diciembre 2025

---

⭐ Si este proyecto te resulta útil, considera darle una estrella en GitHub!
