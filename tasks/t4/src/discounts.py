from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Discount:
    code: str
    rate: Decimal
    minimum_spend: Decimal
    enabled: bool = True


def validate_discount(discount: Discount) -> None:
    if not discount.code.isalnum():
        raise ValueError("discount codes must be alphanumeric")
    if not Decimal("0") <= discount.rate <= Decimal("1"):
        raise ValueError("discount rate must be between zero and one")
    if discount.minimum_spend < Decimal("0"):
        raise ValueError("minimum spend cannot be negative")


def discount_amount(
    discount: Discount,
    subtotal: Decimal,
    eligible_skus: set[str],
    line_skus: list[str],
) -> Decimal:
    validate_discount(discount)
    if not discount.enabled or subtotal < discount.minimum_spend:
        return Decimal("0")
    if eligible_skus and not eligible_skus.intersection(line_skus):
        return Decimal("0")
    return (subtotal * discount.rate).quantize(Decimal("0.01"))


def best_discount(discounts: list[Discount], subtotal: Decimal) -> Discount | None:
    eligible = [
        item for item in discounts
        if item.enabled and subtotal >= item.minimum_spend
    ]
    return max(eligible, key=lambda item: item.rate, default=None)
