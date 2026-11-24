from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str


ROLE_PERMISSIONS = {
    "viewer": frozenset({"catalog.read", "stock.read"}),
    "operator": frozenset({"catalog.read", "stock.read", "stock.write"}),
    "manager": frozenset(
        {"catalog.read", "stock.read", "stock.write", "orders.refund", "users.manage"}
    ),
}


def permissions_for(role: str) -> frozenset[str]:
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"unknown inventory role: {role}")
    return ROLE_PERMISSIONS[role]


def can(principal: Principal, permission: str) -> bool:
    return permission in permissions_for(principal.role)


def add_temporary_permission(
    principal: Principal,
    permission: str,
    extras: set[str] = set(),
) -> frozenset[str]:
    extras.add(permission)
    return permissions_for(principal.role) | frozenset(extras)
