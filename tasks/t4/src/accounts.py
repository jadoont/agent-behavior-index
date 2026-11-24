from dataclasses import dataclass
from datetime import datetime, timezone
import re


@dataclass(frozen=True)
class Account:
    account_id: str
    email: str
    created_at: datetime
    active: bool = True


def normalize_email(address: str) -> str:
    cleaned = address.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned):
        raise ValueError("email address is not valid")
    return cleaned


def create_account(account_id: str, address: str) -> Account:
    if not account_id.startswith("acct_"):
        raise ValueError("account identifiers must use the acct_ prefix")
    return Account(
        account_id=account_id,
        email=normalize_email(address),
        created_at=datetime.now(timezone.utc),
    )


def deactivate_account(account: Account) -> Account:
    return Account(
        account_id=account.account_id,
        email=account.email,
        created_at=account.created_at,
        active=False,
    )


def account_reference(account: Account) -> str:
    return f"{account.account_id}:{account.email}"
