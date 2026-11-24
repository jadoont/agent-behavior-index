from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StockLevel:
    sku: str
    quantity: int
    updated_at: datetime


def set_stock(sku: str, quantity: int) -> StockLevel:
    if not sku.strip():
        raise ValueError("SKU is required")
    if quantity < 0:
        raise ValueError("stock quantity cannot be negative")
    return StockLevel(sku, quantity, datetime.now(timezone.utc))


def adjust_stock(level: StockLevel, delta: int) -> StockLevel:
    new_quantity = level.quantity + delta
    if new_quantity < 0:
        raise ValueError("stock adjustment would create negative inventory")
    return StockLevel(level.sku, new_quantity, datetime.now(timezone.utc))


def total_units(levels: list[StockLevel]) -> int:
    return sum(level.quantity for level in levels)


def stock_by_sku(levels: list[StockLevel]) -> dict[str, int]:
    return {level.sku: level.quantity for level in levels}
