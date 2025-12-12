"""
Script para crear usuarios iniciales en la base de datos
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app.auth import create_user, get_password_hash
from app.models import User, Role, UserRole, Permission, RolePermission
from app.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


def create_admin_user():
    """Crea un usuario administrador por defecto"""
    db = SessionLocal()
    
    try:
        # Inicializar permisos y roles base
        seed_permissions_and_roles(db)

        # Verificar si ya existe un usuario admin
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        # Si ya existe, asegurar que tenga el rol 'admin' asignado
        if existing_admin:
            role_admin = db.query(Role).filter(Role.name == 'admin').first()
            if not role_admin:
                role_admin = Role(name='admin')
                db.add(role_admin)
                db.commit()
                db.refresh(role_admin)

            assoc = db.query(UserRole).filter(UserRole.user_id == existing_admin.id, UserRole.role_id == role_admin.id).first()
            if not assoc:
                assoc = UserRole(user_id=existing_admin.id, role_id=role_admin.id)
                db.add(assoc)
                db.commit()

            print("⚠️  El usuario 'admin' ya existe — rol 'admin' asignado si faltaba")
            return
        
        # Crear usuario admin
        admin = create_user(
            db=db,
            username="admin",
            password="admin123",  # Contraseña temporal - debe cambiarse
            first_name="Admin",
            last_name="Usuario",
            phone="",
            must_change_password=True,
        )
        # Asegurar rol 'admin' y asociarlo
        role_admin = db.query(Role).filter(Role.name == 'admin').first()
        if not role_admin:
            role_admin = Role(name='admin')
            db.add(role_admin)
            db.commit()
            db.refresh(role_admin)

        assoc = db.query(UserRole).filter(UserRole.user_id == admin.id, UserRole.role_id == role_admin.id).first()
        if not assoc:
            assoc = UserRole(user_id=admin.id, role_id=role_admin.id)
            db.add(assoc)
            db.commit()
        
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
        ("analista", "analista123", "Analista", "Prueba", "3000000001"),
        ("auditor", "auditor123", "Auditor", "Prueba", "3000000002"),
        ("consultor", "consultor123", "Consultor", "Prueba", "3000000003"),
    ]
    
    try:
        for username, password, first_name, last_name, phone in test_users:
            # Verificar si ya existe
            existing = db.query(User).filter(User.username == username).first()
            
            if existing:
                print(f"⚠️  El usuario '{username}' ya existe")
                continue
            
            # Crear usuario
            user = create_user(db=db, username=username, password=password, first_name=first_name, last_name=last_name, phone=phone, must_change_password=True)
            print(f"✅ Usuario '{username}' creado (contraseña: {password})")
        
    except Exception as e:
        logger.error(f"Error al crear usuarios de prueba: {e}")
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def seed_permissions_and_roles(db):
    """Crea permisos básicos y roles, asignando permisos a roles"""
    # Permissions list
    permissions = [
        'system.admin',
        'users.view',
        'users.manage',
        'roles.view',
        'roles.manage',
        'permissions.view',
        'permissions.manage',
        'audit.view',
        'config.manage',
        'entities.view',
        'entities.manage',
        'files.upload',
        'files.ingest',
        'files.view',
        'files.delete',
        'comparatives.view',
        'comparatives.export',
        'mapping.view',
        'mapping.manage',
        'alerts.view',
        'alerts.manage',
        'indicators.view'
    ]

    for p in permissions:
        existing = db.query(Permission).filter(Permission.name == p).first()
        if not existing:
            db.add(Permission(name=p, description=""))
    db.commit()

    # Roles mapping
    role_map = {
        'admin': ['system.admin'] + permissions,
        'analista': ['comparatives.view', 'comparatives.export', 'files.view', 'entities.view', 'indicators.view'],
        'auditor': ['audit.view', 'files.view', 'comparatives.view', 'comparatives.export'],
        'uploader': ['files.upload', 'files.ingest', 'files.view'],
        'consultor': ['comparatives.view', 'files.view', 'comparatives.export'],
        'mapping_admin': ['mapping.view', 'mapping.manage', 'files.view'],
        'viewer': ['comparatives.view', 'entities.view', 'files.view'],
    }

    for role_name, perms in role_map.items():
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name)
            db.add(role)
            db.commit()
            db.refresh(role)

        # assign permissions
        for perm_name in perms:
            perm = db.query(Permission).filter(Permission.name == perm_name).first()
            if not perm:
                continue
            # Use INSERT IGNORE to avoid duplicate primary-key errors if association already exists
            try:
                db.execute(text("INSERT IGNORE INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"), {"rid": role.id, "pid": perm.id})
            except Exception:
                # If the DB driver doesn't support INSERT IGNORE or another error occurs,
                # fall back to safe check + add
                assoc = db.query(RolePermission).filter(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id).first()
                if not assoc:
                    assoc = RolePermission(role_id=role.id, permission_id=perm.id)
                    db.add(assoc)
    db.commit()


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
