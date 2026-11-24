from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Parcel:
    weight_kg: Decimal
    postal_code: str
    express: bool = False


def zone_for(postal_code: str) -> int:
    digits = "".join(character for character in postal_code if character.isdigit())
    if not digits:
        raise ValueError("postal code must contain a digit")
    return int(digits[0]) % 5 + 1


def shipping_cost(parcel: Parcel) -> Decimal:
    if parcel.weight_kg <= 0:
        raise ValueError("parcel weight must be positive")
    zone = zone_for(parcel.postal_code)
    base = Decimal("4.50") + Decimal(zone) * Decimal("1.25")
    per_kg = parcel.weight_kg * Decimal("0.80")
    express_fee = Decimal("8.00") if parcel.express else Decimal("0.00")
    return (base + per_kg + express_fee).quantize(Decimal("0.01"))


def parcel_label(parcel: Parcel) -> str:
    service = "express" if parcel.express else "standard"
    return f"{parcel.postal_code.strip().upper()}:{service}:{parcel.weight_kg}"
