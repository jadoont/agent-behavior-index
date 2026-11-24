from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class StockMovement:
    sku: str
    quantity_delta: int
    reference: str


def validate_movement(movement: StockMovement) -> None:
    if not movement.sku.startswith("SKU-"):
        raise ValueError("stock movement needs a catalog SKU")
    if movement.quantity_delta == 0:
        raise ValueError("stock movement cannot be empty")
    if not movement.reference.strip():
        raise ValueError("stock movement needs a reference")


def balances(movements: list[StockMovement]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for movement in movements:
        validate_movement(movement)
        totals[movement.sku] += movement.quantity_delta
    if any(quantity < 0 for quantity in totals.values()):
        raise ValueError("movement history produces negative stock")
    return dict(totals)


def movement_count(movements: list[StockMovement], sku: str) -> int:
    return sum(movement.sku == sku for movement in movements)
