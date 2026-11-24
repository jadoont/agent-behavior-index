from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    unit_price: Decimal
    taxable: bool


@dataclass(frozen=True)
class CartLine:
    product: Product
    quantity: int

    @property
    def extended_price(self) -> Decimal:
        if self.quantity < 1:
            raise ValueError("cart quantities must be positive")
        return self.product.unit_price * self.quantity


@dataclass(frozen=True)
class Receipt:
    order_id: str
    account_id: str
    subtotal: Decimal
    tax: Decimal
    total: Decimal


def line_subtotal(lines: list[CartLine]) -> Decimal:
    return sum((line.extended_price for line in lines), Decimal("0.00"))


def receipt_total(receipt: Receipt) -> Decimal:
    return receipt.subtotal + receipt.tax
