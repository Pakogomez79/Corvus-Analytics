"""
Script de configuración inicial para Corvus XBRL Enterprise
Crea directorios necesarios y verifica la configuración
"""

import os
from pathlib import Path

def create_directory_structure():
    """Crea la estructura de directorios necesaria para la aplicación"""
    
    base_dir = Path(__file__).parent
    directories = [
        "logs",
        "uploads",
        "exports",
        "temp",
        "backups",
        "arelle_cache"
    ]
    
    print("🔧 Configurando Corvus XBRL Enterprise...")
    print("=" * 50)
    
    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Creado: {directory}/")
        else:
            print(f"✓ Existe: {directory}/")
    
    print("=" * 50)
    print("✅ Estructura de directorios configurada correctamente")
    
    # Verificar archivo .env
    env_file = base_dir / ".env"
    env_example = base_dir / ".env.example"
    
    if not env_file.exists():
        print("\n⚠️  ADVERTENCIA: No se encontró archivo .env")
        if env_example.exists():
            print(f"   Por favor, copia {env_example.name} a .env y configura tus variables")
        else:
            print("   Por favor, crea un archivo .env con tus configuraciones")
    else:
        print("\n✓ Archivo .env encontrado")
    
    print("\n🚀 ¡Listo para iniciar la aplicación!")
    print("   Ejecuta: uvicorn app.main:app --reload")

if __name__ == "__main__":
    create_directory_structure()
