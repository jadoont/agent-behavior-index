from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceError:
    code: str
    message: str
    retryable: bool = False


HTTP_STATUS = {
    "invalid_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "missing": 404,
    "conflict": 409,
    "unavailable": 503,
}


def status_code(error: ServiceError) -> int:
    return HTTP_STATUS.get(error.code, 500)


def public_error(error: ServiceError) -> dict[str, object]:
    return {
        "error": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }


def missing_item(sku: str) -> ServiceError:
    return ServiceError("not_found", f"SKU {sku} was not found")


def invalid_quantity(quantity: int) -> ServiceError:
    return ServiceError("invalid_request", f"quantity must be positive, got {quantity}")
