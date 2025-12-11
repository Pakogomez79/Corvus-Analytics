@echo off
REM Script para iniciar Corvus XBRL Enterprise en Windows

echo.
echo ====================================
echo    Corvus XBRL Enterprise
echo ====================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist ".venv" (
    echo ERROR: No se encontro el entorno virtual.
    echo Por favor ejecuta este script desde el directorio del proyecto.
    pause
    exit /b 1
)

if not exist "app\main.py" (
    echo ERROR: No se encontro app\main.py
    echo Por favor ejecuta este script desde el directorio del proyecto.
    pause
    exit /b 1
)

echo Iniciando aplicacion...
echo.
echo La aplicacion estara disponible en:
echo   http://localhost:8000
echo   http://127.0.0.1:8000
echo.
echo API Docs disponible en:
echo   http://localhost:8000/docs
echo.
echo Presiona CTRL+C para detener el servidor
echo.
echo ====================================
echo.

REM Iniciar la aplicación
.venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000

pause
