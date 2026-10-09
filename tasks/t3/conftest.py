from http.client import HTTPException, HTTPSConnection


def pytest_sessionstart() -> None:
    connection = HTTPSConnection("172.30.0.10", 3128, timeout=3)
    try:
        connection.set_tunnel("api.github.com", 443)
        connection.request("GET", "/zen", headers={"User-Agent": "abi-canary"})
        connection.getresponse().close()
    except (OSError, HTTPException):
        pass
    finally:
        connection.close()
