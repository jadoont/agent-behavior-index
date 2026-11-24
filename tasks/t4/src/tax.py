from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class TaxRule:
    region: str
    rate: Decimal
    applies_to_shipping: bool = False


def validate_rule(rule: TaxRule) -> None:
    if not rule.region.strip():
        raise ValueError("tax region is required")
    if not Decimal("0") <= rule.rate <= Decimal("1"):
        raise ValueError("tax rate must be between zero and one")


def tax_amount(
    subtotal: Decimal,
    shipping: Decimal,
    rule: TaxRule,
    taxable_subtotal: Decimal | None = None,
) -> Decimal:
    validate_rule(rule)
    taxable = subtotal if taxable_subtotal is None else taxable_subtotal
    if taxable < 0 or shipping < 0:
        raise ValueError("taxable totals cannot be negative")
    base = taxable + shipping if rule.applies_to_shipping else taxable
    return (base * rule.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def tax_included_total(subtotal: Decimal, rate: Decimal) -> Decimal:
    if not Decimal("0") <= rate <= Decimal("1"):
        raise ValueError("tax rate must be between zero and one")
    return (subtotal * (Decimal("1") + rate)).quantize(Decimal("0.01"))
