"""Autenticación (bcrypt + JWT) y autorización por roles, aplicada en el servidor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(user: Usuario, settings) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user.id), "rol": user.rol, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    settings = request.app.state.settings
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas o sesión vencida",
                                 headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized from None
    user = db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise unauthorized
    return user


def require_roles(*roles: str):
    """Dependencia: permite el acceso solo a los roles indicados."""
    def checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.rol not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Acción no permitida para el rol '{user.rol}'")
        return user
    return checker


ADMIN = ("admin",)
RESEARCH = ("admin", "investigador")
ANY = ("admin", "investigador", "eps")
