from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int
    field: str
    message: str


def validate_quantity(value: object, row_number: int) -> ValidationIssue | None:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount != amount.to_integral_value():
            return ValidationIssue(row_number, "quantity", "must be a whole number")
        quantity = int(amount)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return ValidationIssue(row_number, "quantity", "must be a whole number")
    if quantity < 0:
        return ValidationIssue(row_number, "quantity", "cannot be negative")
    return None


def validate_price(value: object, row_number: int) -> ValidationIssue | None:
    try:
        amount = Decimal(str(value))
    except Exception:
        return ValidationIssue(row_number, "unit_price", "must be a decimal amount")
    if not amount.is_finite():
        return ValidationIssue(row_number, "unit_price", "must be a finite decimal amount")
    if amount < 0:
        return ValidationIssue(row_number, "unit_price", "cannot be negative")
    return None


def completion_percent(checked: int, total: int) -> float:
    if total <= 0 or checked < 0 or checked > total:
        raise ValueError("validation counts are inconsistent")
    return checked // total * 100.0


def collect_issues(rows: Iterable[dict[str, object]]) -> list[ValidationIssue]:
    problems = []
    for row_number, row in enumerate(rows, start=1):
        for field, validator in (("quantity", validate_quantity), ("unit_price", validate_price)):
            issue = validator(row.get(field), row_number)
            if issue is not None:
                problems.append(issue)
    return problems
