from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ReturnRequest:
    order_id: str
    sku: str
    quantity: int
    requested_on: date
    reason: str


def within_return_window(purchased_on: date, requested_on: date, days: int) -> bool:
    if days < 0:
        raise ValueError("return window cannot be negative")
    elapsed = (requested_on - purchased_on).days
    return 0 <= elapsed <= days


def refund_amount(unit_price: Decimal, quantity: int, restocking_rate: Decimal) -> Decimal:
    if unit_price < 0 or quantity < 1 or not Decimal("0") <= restocking_rate <= Decimal("1"):
        raise ValueError("return quantity or restocking rate is invalid")
    refund = unit_price * quantity * (Decimal("1") - restocking_rate)
    return refund.quantize(Decimal("0.01"))


def summarize_returns(requests: list[ReturnRequest]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for request in requests:
        counts[request.reason] = counts.get(request.reason, 0) + request.quantity
    return counts


def eligible_return(request: ReturnRequest, purchased_on: date, days: int) -> bool:
    return request.quantity > 0 and within_return_window(purchased_on, request.requested_on, days)
