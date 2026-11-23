"""Política de permisos para adaptadores. No sustituye autenticación."""
from dataclasses import dataclass
from typing import Literal

Permission = Literal["memory:read", "memory:write", "memory:delete", "action:execute"]

@dataclass(frozen=True)
class Principal:
    owner_id: str
    permissions: frozenset[str]

    def __post_init__(self):
        if not self.owner_id.strip():
            raise ValueError("identidad requerida")

def require_permission(principal: Principal, permission: Permission) -> None:
    if permission not in principal.permissions:
        raise PermissionError(f"permiso requerido: {permission}")
