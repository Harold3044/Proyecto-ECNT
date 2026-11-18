"""Autenticación y gestión de usuarios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import ROLES, Usuario
from ecnt_api.security import ADMIN, create_token, get_current_user, hash_password, require_roles, verify_password
from ecnt_api.utils import audit, clean_json

router = APIRouter(tags=["autenticación"])


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=200)
    rol: str
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    activo: bool | None = None
    rol: str | None = None


def user_dict(u: Usuario) -> dict:
    return clean_json({"id": u.id, "email": u.email, "nombre": u.nombre, "rol": u.rol, "activo": u.activo,
                       "creado": u.creado})


@router.post("/auth/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalars(select(Usuario).where(Usuario.email == form.username.lower().strip())).first()
    if user is None or not user.activo or not verify_password(form.password, user.password_hash):
        audit(db, None, "login_fallido", "auth", {"email": form.username}, request)
        db.commit()
        raise HTTPException(401, "Correo o contraseña incorrectos")
    audit(db, user, "login", "auth", request=request)
    db.commit()
    return {"access_token": create_token(user, request.app.state.settings), "token_type": "bearer",
            "usuario": user_dict(user)}


@router.get("/auth/me")
def me(user: Usuario = Depends(get_current_user)):
    return user_dict(user)


@router.get("/users", dependencies=[Depends(require_roles(*ADMIN))])
def list_users(db: Session = Depends(get_db)):
    return [user_dict(u) for u in db.scalars(select(Usuario).order_by(Usuario.id)).all()]


@router.post("/users", status_code=201)
def create_user(body: UserCreate, request: Request, db: Session = Depends(get_db),
                admin: Usuario = Depends(require_roles(*ADMIN))):
    if body.rol not in ROLES:
        raise HTTPException(400, f"Rol inválido. Opciones: {ROLES}")
    if db.scalars(select(Usuario).where(Usuario.email == body.email.lower())).first():
        raise HTTPException(409, "Ya existe un usuario con ese correo")
    u = Usuario(email=body.email.lower(), nombre=body.nombre, rol=body.rol, password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    audit(db, admin, "crear_usuario", f"usuario:{u.id}", {"rol": u.rol}, request)
    db.commit()
    return user_dict(u)


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, request: Request, db: Session = Depends(get_db),
                admin: Usuario = Depends(require_roles(*ADMIN))):
    u = db.get(Usuario, user_id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    if u.id == admin.id and (body.activo is False or (body.rol and body.rol != "admin")):
        raise HTTPException(400, "No puede desactivarse ni quitarse el rol de administrador a sí mismo")
    if body.rol is not None:
        if body.rol not in ROLES:
            raise HTTPException(400, f"Rol inválido. Opciones: {ROLES}")
        u.rol = body.rol
    if body.activo is not None:
        u.activo = body.activo
    audit(db, admin, "actualizar_usuario", f"usuario:{u.id}", body.model_dump(exclude_none=True), request)
    db.commit()
    return user_dict(u)
