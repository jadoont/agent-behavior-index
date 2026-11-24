from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    name: str
    contact_email: str
    lead_days: int


def validate_vendor(vendor: Vendor) -> None:
    if not vendor.vendor_id.startswith("ven_"):
        raise ValueError("vendor identifier must use the ven_ prefix")
    if not vendor.name.strip() or "@" not in vendor.contact_email:
        raise ValueError("vendor name and contact email are required")
    if vendor.lead_days < 0:
        raise ValueError("vendor lead time cannot be negative")


def reorder_cost(unit_cost: Decimal, units: int, handling_fee: Decimal) -> Decimal:
    if unit_cost < 0 or units < 0 or handling_fee < 0:
        raise ValueError("reorder costs and quantity cannot be negative")
    return unit_cost * units + handling_fee


def vendors_by_id(vendors: list[Vendor]) -> dict[str, Vendor]:
    indexed = {vendor.vendor_id: vendor for vendor in vendors}
    if len(indexed) != len(vendors):
        raise ValueError("vendor identifiers must be unique")
    return indexed
