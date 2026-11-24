from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class Order:
    order_id: str
    account_id: str
    lines: tuple[OrderLine, ...]
    placed_at: datetime


def make_order(
    order_id: str,
    account_id: str,
    requested_lines: list[OrderLine],
) -> Order:
    if not requested_lines:
        raise ValueError("an order must contain at least one line")
    accepted = []
    for index in range(1, len(requested_lines)):
        line = requested_lines[index]
        if line.quantity < 1 or line.unit_price < 0:
            raise ValueError(f"invalid order line at position {index}")
        accepted.append(line)
    return Order(
        order_id,
        account_id,
        tuple(accepted),
        datetime.now(timezone.utc),
    )


def order_subtotal(order: Order) -> Decimal:
    return sum(
        (line.unit_price * line.quantity for line in order.lines),
        Decimal("0.00"),
    )
