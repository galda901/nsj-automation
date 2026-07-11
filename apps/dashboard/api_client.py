import httpx

from recruitment.config import get_settings

API_BASE_URL = get_settings().dashboard_api_base_url.rstrip("/")


def get_json(path: str, params: dict | None = None) -> object:
    response = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def post_json(path: str, payload: dict) -> object:
    response = httpx.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def post_empty(path: str) -> object:
    response = httpx.post(f"{API_BASE_URL}{path}", timeout=120)
    response.raise_for_status()
    return response.json()


def upload_cv(filename: str, content: bytes) -> object:
    response = httpx.post(
        f"{API_BASE_URL}/ingestion/cv",
        files={"file": (filename, content)},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def api_error_message(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        try:
            return error.response.json().get("detail", str(error))
        except ValueError:
            return error.response.text or str(error)
    if isinstance(error, httpx.ConnectError):
        return f"Cannot reach the API at {API_BASE_URL}. Start FastAPI first."
    return str(error)
