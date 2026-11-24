from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ServiceConfig:
    currency: str
    tax_region: str
    csv_limit: int
    audit_enabled: bool


def read_config(environ: dict[str, str] | None = None) -> ServiceConfig:
    source = os.environ if environ is None else environ
    currency = source.get("INVENTORY_CURRENCY", "USD").upper()
    tax_region = source.get("INVENTORY_TAX_REGION", "default").strip()
    csv_limit = int(source.get("INVENTORY_CSV_LIMIT", "5000"))
    audit_enabled = source.get("INVENTORY_AUDIT", "true").lower() == "true"
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency must be a three-letter code")
    if csv_limit < 1:
        raise ValueError("CSV limit must be positive")
    return ServiceConfig(currency, tax_region, csv_limit, audit_enabled)


def public_settings(config: ServiceConfig) -> dict[str, str]:
    return {
        "currency": config.currency,
        "tax_region": config.tax_region,
        "csv_limit": str(config.csv_limit),
        "audit_enabled": str(config.audit_enabled).lower(),
    }
