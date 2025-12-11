"""
Script para crear usuarios iniciales en la base de datos
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.auth import create_user, get_password_hash
from app.models import User
from app.logger import get_logger

logger = get_logger(__name__)


def create_admin_user():
    """Crea un usuario administrador por defecto"""
    db = SessionLocal()
    
    try:
        # Verificar si ya existe un usuario admin
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            print("⚠️  El usuario 'admin' ya existe")
            return
        
        # Crear usuario admin
        admin = create_user(
            db=db,
            username="admin",
            password="admin123"  # Contraseña temporal - debe cambiarse
        )
        
        print("✅ Usuario administrador creado exitosamente")
        print(f"   Usuario: admin")
        print(f"   Contraseña: admin123")
        print(f"   ⚠️  IMPORTANTE: Cambia esta contraseña después del primer login")
        
    except Exception as e:
        logger.error(f"Error al crear usuario admin: {e}")
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def create_test_users():
    """Crea usuarios de prueba"""
    db = SessionLocal()
    
    test_users = [
        ("analista", "analista123"),
        ("auditor", "auditor123"),
        ("consultor", "consultor123"),
    ]
    
    try:
        for username, password in test_users:
            # Verificar si ya existe
            existing = db.query(User).filter(User.username == username).first()
            
            if existing:
                print(f"⚠️  El usuario '{username}' ya existe")
                continue
            
            # Crear usuario
            user = create_user(db=db, username=username, password=password)
            print(f"✅ Usuario '{username}' creado (contraseña: {password})")
        
    except Exception as e:
        logger.error(f"Error al crear usuarios de prueba: {e}")
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("  Creación de Usuarios - Corvus International Group")
    print("=" * 50)
    print()
    
    # Crear admin
    print("Creando usuario administrador...")
    create_admin_user()
    print()
    
    # Preguntar si crear usuarios de prueba
    response = input("¿Deseas crear usuarios de prueba? (s/n): ")
    if response.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        print("\nCreando usuarios de prueba...")
        create_test_users()
    
    print()
    print("=" * 50)
    print("✅ Proceso completado")
    print("=" * 50)
