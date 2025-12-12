from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    nit = Column(String(50), nullable=True, unique=True)
    sector = Column(String(100), nullable=True)
    type = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = relationship("File", back_populates="entity")


class Period(Base):
    __tablename__ = "periods"

    id = Column(Integer, primary_key=True)
    start = Column(Date, nullable=False)
    end = Column(Date, nullable=False)
    frequency = Column(String(20), nullable=True)  # e.g., annual, quarterly

    files = relationship("File", back_populates="period")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    taxonomy = Column(String(100), nullable=True)
    version = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True)
    warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    period_id = Column(Integer, ForeignKey("periods.id"), nullable=True)

    entity = relationship("Entity", back_populates="files")
    period = relationship("Period", back_populates="files")
    facts = relationship("Fact", back_populates="file", cascade="all, delete-orphan")


class Fact(Base):
    __tablename__ = "facts"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    concept_qname = Column(String(255), nullable=False)
    canonical_concept = Column(String(255), nullable=True)
    value = Column(Numeric(24, 4), nullable=True)
    decimals = Column(Integer, nullable=True)
    unit = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True)
    dimensions = Column(JSON, nullable=True)

    file = relationship("File", back_populates="facts")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # New profile/contact fields
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    # Password lifecycle
    must_change_password = Column(Boolean, default=False)
    password_changed_at = Column(DateTime, nullable=True)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    # Permisos individuales (overrides/extra permissions)
    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    # Permisos asociados al rol
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    users = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class UserPermission(Base):
    __tablename__ = "user_permissions"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)

    user = relationship("User", back_populates="permissions")
    permission = relationship("Permission", back_populates="users")
