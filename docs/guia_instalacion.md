# Guía de Instalación Detallada - Corvus XBRL Enterprise

**Versión**: 1.0.0  
**Fecha**: Diciembre 2025  
**Actualizado**: 10 de diciembre de 2025

---

## 📋 Tabla de Contenidos

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación en Windows](#instalación-en-windows)
3. [Instalación en Linux](#instalación-en-linux)
4. [Configuración de Base de Datos](#configuración-de-base-de-datos)
5. [Configuración de Variables de Entorno](#configuración-de-variables-de-entorno)
6. [Ejecución de Migraciones](#ejecución-de-migraciones)
7. [Primera Ejecución](#primera-ejecución)
8. [Verificación de Instalación](#verificación-de-instalación)
9. [Solución de Problemas](#solución-de-problemas)

---

## Requisitos del Sistema

### Hardware Mínimo
- **Procesador**: 2 núcleos, 2.0 GHz
- **RAM**: 2 GB
- **Disco**: 500 MB libres
- **Red**: Conexión a internet para instalación

### Hardware Recomendado
- **Procesador**: 4 núcleos, 2.5 GHz o superior
- **RAM**: 4 GB o más
- **Disco**: 2 GB libres (incluye espacio para archivos XBRL)
- **Red**: Conexión estable para descarga de taxonomías

### Software Requerido

#### Sistema Operativo
- Windows 10/11 (64-bit)
- Windows Server 2019/2022
- Ubuntu 20.04 LTS o superior
- Debian 11 o superior
- CentOS 8 o superior

#### Python
- **Versión**: Python 3.10, 3.11 o 3.12
- **NO compatible**: Python 3.9 o anterior, Python 3.13 (no probado)

#### Base de Datos
Elige una de las siguientes opciones:

**Opción 1: MySQL (Recomendado)**
- MySQL 5.7 o superior
- MySQL 8.0 (recomendado)
- MariaDB 10.5 o superior

**Opción 2: SQL Server**
- SQL Server 2017 o superior
- SQL Server 2019 (recomendado)
- SQL Server Express (para desarrollo)

---

## Instalación en Windows

### Paso 1: Instalar Python

1. Descargar Python desde [python.org](https://www.python.org/downloads/)
2. Ejecutar el instalador
3. **IMPORTANTE**: Marcar "Add Python to PATH"
4. Verificar instalación:

```powershell
python --version
# Debe mostrar: Python 3.10.x o superior
```

### Paso 2: Instalar MySQL

1. Descargar MySQL Installer desde [mysql.com](https://dev.mysql.com/downloads/installer/)
2. Ejecutar instalador y seleccionar "Custom"
3. Instalar componentes:
   - MySQL Server 8.0
   - MySQL Workbench (opcional, para gestión visual)
4. Durante configuración:
   - Puerto: 3306 (default)
   - Usuario: root
   - Contraseña: (anotar para uso posterior)
5. Verificar instalación:

```powershell
mysql --version
```

### Paso 3: Clonar el Repositorio

```powershell
# Instalar Git si no lo tienes
winget install Git.Git

# Clonar repositorio
cd "C:\Users\TuUsuario\Documents"
git clone https://github.com/tu-usuario/Corvus-Analytics.git
cd Corvus-Analytics
```

### Paso 4: Crear Entorno Virtual

```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
.venv\Scripts\activate

# Verificar activación (debe aparecer (.venv) en el prompt)
```

### Paso 5: Instalar Dependencias

```powershell
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
pip list
```

### Paso 6: Configurar Variables de Entorno

```powershell
# Copiar archivo de ejemplo
copy .env.example .env

# Editar .env con Notepad
notepad .env
```

Configurar las siguientes variables:

```env
# Base de Datos
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=xbrl_analytics
DATABASE_USER=root
DATABASE_PASSWORD=tu_password_mysql

# Aplicación
APP_NAME=Corvus XBRL Enterprise
DEBUG=True
SECRET_KEY=genera-clave-segura-aqui

# Logging
LOG_LEVEL=INFO
```

### Paso 7: Crear Base de Datos

```powershell
# Conectar a MySQL
mysql -u root -p

# En la consola MySQL, ejecutar:
```

```sql
CREATE DATABASE xbrl_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SHOW DATABASES;
EXIT;
```

### Paso 8: Ejecutar Setup

```powershell
# Crear directorios necesarios
python setup.py
```

### Paso 9: Ejecutar Migraciones

```powershell
# Aplicar migraciones a la base de datos
alembic upgrade head

# Verificar que se crearon las tablas
mysql -u root -p xbrl_analytics -e "SHOW TABLES;"
```

### Paso 10: Iniciar Aplicación

```powershell
# Iniciar servidor de desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir navegador en: `http://localhost:8000`

---

## Instalación en Linux

### Paso 1: Instalar Python y Dependencias del Sistema

**Ubuntu/Debian:**

```bash
# Actualizar repositorios
sudo apt update

# Instalar Python y herramientas
sudo apt install python3.10 python3.10-venv python3-pip
sudo apt install git curl

# Instalar dependencias para MySQL
sudo apt install libmysqlclient-dev
```

**CentOS/RHEL:**

```bash
sudo yum update
sudo yum install python3.10 python3-pip git
sudo yum install mysql-devel
```

### Paso 2: Instalar MySQL

**Ubuntu/Debian:**

```bash
# Instalar MySQL Server
sudo apt install mysql-server

# Iniciar servicio
sudo systemctl start mysql
sudo systemctl enable mysql

# Configuración segura
sudo mysql_secure_installation
```

**CentOS/RHEL:**

```bash
sudo yum install mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

### Paso 3: Clonar y Configurar Proyecto

```bash
# Clonar repositorio
cd /opt
sudo git clone https://github.com/tu-usuario/Corvus-Analytics.git
cd Corvus-Analytics

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 4: Configurar Base de Datos

```bash
# Conectar a MySQL
sudo mysql -u root -p

# Crear base de datos
```

```sql
CREATE DATABASE xbrl_analytics CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'corvus'@'localhost' IDENTIFIED BY 'password_seguro';
GRANT ALL PRIVILEGES ON xbrl_analytics.* TO 'corvus'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Paso 5: Configurar Variables

```bash
# Copiar y editar .env
cp .env.example .env
nano .env  # o usar vi, vim, etc.
```

### Paso 6: Setup y Migraciones

```bash
# Ejecutar setup
python setup.py

# Aplicar migraciones
alembic upgrade head
```

### Paso 7: Crear Servicio Systemd (Producción)

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/corvus-xbrl.service
```

Contenido del archivo:

```ini
[Unit]
Description=Corvus XBRL Enterprise
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/Corvus-Analytics
Environment="PATH=/opt/Corvus-Analytics/.venv/bin"
ExecStart=/opt/Corvus-Analytics/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable corvus-xbrl
sudo systemctl start corvus-xbrl
sudo systemctl status corvus-xbrl
```

---

## Configuración de Base de Datos

### MySQL

#### Configuración Óptima (my.cnf o my.ini)

```ini
[mysqld]
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
max_connections=150
innodb_buffer_pool_size=256M
innodb_log_file_size=64M
```

#### Crear Usuario Específico

```sql
CREATE USER 'corvus_user'@'localhost' IDENTIFIED BY 'password_muy_seguro';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER ON xbrl_analytics.* TO 'corvus_user'@'localhost';
FLUSH PRIVILEGES;
```

### SQL Server

#### Configuración en .env

```env
DATABASE_TYPE=mssql
DATABASE_HOST=localhost
DATABASE_PORT=1433
DATABASE_NAME=xbrl_analytics
DATABASE_USER=corvus_user
DATABASE_PASSWORD=password_seguro
DATABASE_DRIVER=ODBC Driver 17 for SQL Server
```

#### Instalar Driver ODBC (Windows)

Descargar desde: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

#### Crear Base de Datos

```sql
CREATE DATABASE xbrl_analytics;
GO

CREATE LOGIN corvus_user WITH PASSWORD = 'password_seguro';
GO

USE xbrl_analytics;
CREATE USER corvus_user FOR LOGIN corvus_user;
ALTER ROLE db_owner ADD MEMBER corvus_user;
GO
```

---

## Configuración de Variables de Entorno

### Variables Requeridas

```env
# Base de Datos (REQUERIDO)
DATABASE_TYPE=mysql              # mysql o mssql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=xbrl_analytics
DATABASE_USER=root
DATABASE_PASSWORD=tu_password

# Seguridad (REQUERIDO)
SECRET_KEY=genera-una-clave-segura-de-32-caracteres-o-mas
```

### Variables Opcionales

```env
# Aplicación
APP_NAME=Corvus XBRL Enterprise
APP_VERSION=1.0.0
DEBUG=False
HOST=0.0.0.0
PORT=8000

# Logging
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=standard              # standard o json
LOG_FILE=logs/corvus.log
LOG_MAX_BYTES=10485760          # 10MB
LOG_BACKUP_COUNT=5

# Archivos
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIRECTORY=uploads/
EXPORT_DIRECTORY=exports/

# Email (para recuperación de contraseña)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_password
MAIL_FROM=noreply@corvus-xbrl.com
MAIL_TLS=True
```

### Generar SECRET_KEY Seguro

**Python:**
```python
import secrets
print(secrets.token_urlsafe(32))
```

**PowerShell:**
```powershell
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

---

## Ejecución de Migraciones

### Comandos Básicos

```bash
# Ver estado actual
alembic current

# Ver historial de migraciones
alembic history

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Aplicar una migración específica
alembic upgrade <revision_id>

# Revertir última migración
alembic downgrade -1

# Revertir todas las migraciones
alembic downgrade base
```

### Crear Nueva Migración

```bash
# Generar migración automáticamente
alembic revision --autogenerate -m "Descripción del cambio"

# Crear migración vacía
alembic revision -m "Descripción del cambio"

# Revisar archivo generado en alembic/versions/
```

---

## Primera Ejecución

### Modo Desarrollo

```bash
# Activar entorno virtual
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Iniciar con recarga automática
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Modo Producción

```bash
# Con Gunicorn (Linux)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Con Hypercorn
hypercorn app.main:app --bind 0.0.0.0:8000 --workers 4
```

### Acceder a la Aplicación

- **Interfaz Web**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Verificación de Instalación

### Checklist de Verificación

```bash
# 1. Verificar Python
python --version

# 2. Verificar entorno virtual activo
which python  # Linux/Mac
where python  # Windows

# 3. Verificar dependencias instaladas
pip list | grep fastapi
pip list | grep sqlalchemy
pip list | grep alembic

# 4. Verificar conexión a base de datos
python -c "from app.db import engine; print('✅ Conexión exitosa' if engine.connect() else '❌ Error')"

# 5. Verificar directorios
ls -la logs/ uploads/ exports/  # Linux/Mac
dir logs, uploads, exports      # Windows

# 6. Verificar migraciones
alembic current

# 7. Verificar tablas en BD
mysql -u root -p xbrl_analytics -e "SHOW TABLES;"
```

### Script de Verificación

```python
# verificar.py
import sys
from pathlib import Path

def verificar_instalacion():
    checks = []
    
    # Python version
    if sys.version_info >= (3, 10):
        checks.append("✅ Python version OK")
    else:
        checks.append("❌ Python version incorrecta")
    
    # Directorios
    for dir in ["logs", "uploads", "exports"]:
        if Path(dir).exists():
            checks.append(f"✅ Directorio {dir}/ existe")
        else:
            checks.append(f"❌ Directorio {dir}/ no existe")
    
    # .env
    if Path(".env").exists():
        checks.append("✅ Archivo .env existe")
    else:
        checks.append("❌ Archivo .env no existe")
    
    # Base de datos
    try:
        from app.db import engine
        engine.connect()
        checks.append("✅ Conexión a BD exitosa")
    except Exception as e:
        checks.append(f"❌ Error conexión BD: {e}")
    
    for check in checks:
        print(check)

if __name__ == "__main__":
    verificar_instalacion()
```

---

## Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'app'"

**Causa**: Entorno virtual no activado o instalación incompleta

**Solución**:
```bash
# Activar entorno virtual
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: "Can't connect to MySQL server"

**Causa**: MySQL no está corriendo o credenciales incorrectas

**Solución**:
```bash
# Windows
net start MySQL80

# Linux
sudo systemctl start mysql

# Verificar credenciales en .env
mysql -u root -p
```

### Error: "alembic: command not found"

**Causa**: Entorno virtual no activado

**Solución**:
```bash
source .venv/bin/activate
which alembic  # Debe mostrar ruta dentro de .venv
```

### Error: "Port 8000 already in use"

**Causa**: Puerto ocupado por otra aplicación

**Solución**:
```bash
# Cambiar puerto
uvicorn app.main:app --port 8001

# O matar proceso existente (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux
lsof -ti:8000 | xargs kill
```

### Error: "permission denied" al crear directorios

**Causa**: Permisos insuficientes

**Solución Linux**:
```bash
sudo chown -R $USER:$USER .
chmod -R 755 .
```

### Error de importación de Arelle

**Causa**: Instalación incompleta de arelle-release

**Solución**:
```bash
pip uninstall arelle-release
pip install --no-cache-dir arelle-release>=2.25.0
```

### Problemas con logs/

**Síntoma**: Errores al escribir logs

**Solución**:
```bash
# Crear directorio manualmente
mkdir -p logs
chmod 755 logs

# Verificar permisos
ls -ld logs/
```

---

## Contacto y Soporte

Para asistencia adicional:
- **Email**: soporte@tu-empresa.com
- **Issues**: GitHub Issues
- **Documentación**: [Link a docs]

---

**Última actualización**: 10 de diciembre de 2025  
**Versión del documento**: 1.0
