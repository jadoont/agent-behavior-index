from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def line_price(unit_price: Decimal, quantity: int) -> Decimal:
    if unit_price < Decimal("0"):
        raise ValueError("unit price cannot be negative")
    if quantity < 0:
        raise ValueError("quantity cannot be negative")
    return money(unit_price * quantity)


def subtotal(lines: list[tuple[Decimal, int]]) -> Decimal:
    total = Decimal("0.00")
    for unit_price, quantity in lines:
        total += line_price(unit_price, quantity)
    return money(total)


def apply_adjustment(amount: Decimal, adjustment: Decimal) -> Decimal:
    result = amount + adjustment
    if result < 0:
        raise ValueError("price adjustment cannot make a negative total")
    return money(result)


def format_price(amount: Decimal, currency: str = "USD") -> str:
    return f"{currency.upper()} {money(amount):.2f}"
