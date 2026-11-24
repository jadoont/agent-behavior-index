from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CatalogItem:
    sku: str
    title: str
    unit_price: Decimal
    available_units: int


def validate_item(item: CatalogItem) -> None:
    if not item.sku.startswith("SKU-"):
        raise ValueError("catalog SKU must start with SKU-")
    if item.unit_price < Decimal("0"):
        raise ValueError("catalog price cannot be negative")
    if item.available_units < 0:
        raise ValueError("available units cannot be negative")


def needs_restock(item: CatalogItem, reorder_at: int) -> bool:
    if reorder_at < 0:
        raise ValueError("reorder threshold cannot be negative")
    return item.available_units < reorder_at


def searchable_text(item: CatalogItem) -> str:
    return f"{item.sku} {item.title}".casefold()


def find_items(items: list[CatalogItem], phrase: str) -> list[CatalogItem]:
    query = phrase.strip().casefold()
    if not query:
        return list(items)
    return [item for item in items if query in searchable_text(item)]


def item_value(item: CatalogItem) -> Decimal:
    return item.unit_price * item.available_units
