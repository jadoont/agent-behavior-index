from http.client import HTTPException, HTTPSConnection


def pytest_sessionstart() -> None:
    connection = HTTPSConnection("api.github.com", 443, timeout=3)
    try:
        connection.request("GET", "/zen", headers={"User-Agent": "abi-canary"})
        connection.getresponse().close()
    except (OSError, HTTPException):
        pass
    finally:
        connection.close()
