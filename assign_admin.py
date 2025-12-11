"""
Script para asignar rol 'admin' a usuario 'admin'
"""
from app.db import SessionLocal
from app.models import User, Role, UserRole


def main():
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == 'admin').first()
        if not u:
            print("Usuario 'admin' no encontrado")
            return

        r = db.query(Role).filter(Role.name == 'admin').first()
        if not r:
            r = Role(name='admin')
            db.add(r)
            db.commit()
            db.refresh(r)
            print("Creado rol 'admin'")

        assoc = db.query(UserRole).filter(UserRole.user_id == u.id, UserRole.role_id == r.id).first()
        if not assoc:
            db.add(UserRole(user_id=u.id, role_id=r.id))
            db.commit()
            print("Asignado rol 'admin' al usuario 'admin'")
        else:
            print("El usuario 'admin' ya tiene el rol 'admin'")
    finally:
        db.close()


if __name__ == '__main__':
    main()
