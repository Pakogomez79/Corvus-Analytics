"""
Módulo de autenticación para Corvus International Group
Maneja JWT tokens, validación de usuarios y sesiones
"""

from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .models import User, Permission, Role, RolePermission, UserPermission, UserRole
from .logger import get_logger

logger = get_logger(__name__)

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Contexto para hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de seguridad para tokens
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña coincide con su hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña"""
    # Truncar password si es muy larga (bcrypt tiene límite de 72 bytes)
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)



def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT con los datos proporcionados
    
    Args:
        data: Diccionario con los datos a incluir en el token
        expires_delta: Tiempo de expiración opcional
        
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Token creado para usuario: {data.get('sub')}")
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decodifica un token JWT
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        Diccionario con los datos del token o None si es inválido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Error al decodificar token: {e}")
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Autentica un usuario con sus credenciales
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario
        password: Contraseña en texto plano
        
    Returns:
        Usuario si las credenciales son correctas, None en caso contrario
    """
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        logger.warning(f"Usuario no encontrado: {username}")
        return None
    
    if not user.is_active:
        logger.warning(f"Usuario inactivo intentó acceder: {username}")
        return None
    
    if not verify_password(password, user.password_hash):
        logger.warning(f"Contraseña incorrecta para usuario: {username}")
        return None
    
    logger.info(f"Usuario autenticado exitosamente: {username}")
    return user


def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = None
) -> Optional[dict]:
    """
    Extrae el usuario actual desde el token JWT
    
    Args:
        credentials: Credenciales HTTP Bearer
        db: Sesión de base de datos (opcional)
        
    Returns:
        Datos del usuario del token
        
    Raises:
        HTTPException: Si el token es inválido o expirado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        if payload is None:
            raise credentials_exception
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        return payload
        
    except JWTError:
        raise credentials_exception


def create_user(db: Session, username: str, password: str, first_name: Optional[str] = None, last_name: Optional[str] = None, phone: Optional[str] = None, must_change_password: bool = False) -> User:
    """
    Crea un nuevo usuario en la base de datos
    
    Args:
        db: Sesión de base de datos
        username: Nombre de usuario
        password: Contraseña en texto plano
        email: Email opcional
        
    Returns:
        Usuario creado
    """
    # Verificar si el usuario ya existe
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise ValueError(f"El usuario {username} ya existe")
    
    # Crear nuevo usuario
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        password_hash=hashed_password,
        is_active=True,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        must_change_password=must_change_password,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Usuario creado: {username}")
    return new_user


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
    """
    Cambia la contraseña de un usuario
    
    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        old_password: Contraseña actual
        new_password: Nueva contraseña
        
    Returns:
        True si el cambio fue exitoso, False en caso contrario
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        logger.warning(f"Usuario no encontrado con ID: {user_id}")
        return False
    
    # Verificar contraseña actual
    if not verify_password(old_password, user.password_hash):
        logger.warning(f"Contraseña actual incorrecta para usuario ID: {user_id}")
        return False
    
    # Actualizar contraseña
    user.password_hash = get_password_hash(new_password)
    # Marcar que ya cambió la contraseña y guardar fecha
    user.must_change_password = False
    user.password_changed_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Contraseña cambiada para usuario ID: {user_id}")
    return True


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña
    
    Args:
        password: Contraseña a validar
        
    Returns:
        Tupla (es_válida, mensaje)
    """
    min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    
    if len(password) < min_length:
        return False, f"La contraseña debe tener al menos {min_length} caracteres"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if os.getenv("PASSWORD_REQUIRE_UPPERCASE", "True") == "True" and not has_upper:
        return False, "La contraseña debe contener al menos una letra mayúscula"
    
    if os.getenv("PASSWORD_REQUIRE_LOWERCASE", "True") == "True" and not has_lower:
        return False, "La contraseña debe contener al menos una letra minúscula"
    
    if os.getenv("PASSWORD_REQUIRE_NUMBERS", "True") == "True" and not has_digit:
        return False, "La contraseña debe contener al menos un número"
    
    if os.getenv("PASSWORD_REQUIRE_SPECIAL", "True") == "True" and not has_special:
        return False, "La contraseña debe contener al menos un carácter especial"
    
    return True, "Contraseña válida"


def has_permission(db: Session, user_id: int, permission_name: str) -> bool:
    """
    Verifica si el usuario tiene un permiso específico.
    Revisa primero permisos directos del usuario y luego permisos por rol.
    """
    if not user_id or not permission_name:
        return False

    # Revisar permisos directos de usuario
    up = (
        db.query(UserPermission)
        .join(Permission)
        .filter(UserPermission.user_id == user_id, Permission.name == permission_name)
        .first()
    )
    if up:
        return True

    # Revisar permisos por rol
    rp = (
        db.query(Permission)
        .join(RolePermission)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id, Permission.name == permission_name)
        .first()
    )
    return bool(rp)
