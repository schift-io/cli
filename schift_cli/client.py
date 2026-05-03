from __future__ import annotations

from typing import Any

import click
import httpx

from schift_cli.config import get_api_key, get_api_url

# Timeout: 30s connect, 120s read (migrations can be slow)
DEFAULT_TIMEOUT = httpx.Timeout(30.0, read=120.0)


class SchiftAPIError(Exception):
    """Raised when the Schift API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class SchiftClient:
    """HTTP client for the Schift API.

    Handles authentication headers, base URL resolution, and consistent
    error handling so command modules can stay focused on CLI logic.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        if api_key is not None:
            if not api_key:
                raise click.ClickException("API key cannot be empty.")
            self.api_key = api_key
        else:
            self.api_key = get_api_key()
        self.base_url = (base_url or get_api_url()).rstrip("/")
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=DEFAULT_TIMEOUT,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "User-Agent": "schift-cli/0.1.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # -- HTTP verbs ----------------------------------------------------------

    def get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def post_multipart(self, path: str, *, data: dict[str, Any] | None = None, files: Any = None) -> Any:
        return self._request("POST", path, data=data, files=files)

    def put(self, path: str, **kwargs: Any) -> Any:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)

    # -- Internal -------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            resp = self._http.request(method, path, **kwargs)
        except httpx.ConnectError:
            raise click.ClickException(
                f"Could not connect to Schift API at {self.base_url}\n"
                "  The server may be unavailable. Check your network or set "
                "SCHIFT_API_URL if using a custom endpoint."
            )
        except httpx.TimeoutException:
            raise click.ClickException(
                "Request timed out. The server may be under heavy load — try again."
            )

        if resp.status_code == 401:
            raise click.ClickException(
                "Authentication failed. Run `schift auth login` to set your API key."
            )

        if resp.status_code >= 400:
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("message") or resp.text
            except Exception:
                detail = resp.text
            raise SchiftAPIError(resp.status_code, str(detail))

        if resp.status_code == 204:
            return None
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SchiftClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def require_api_key(api_key: str | None = None) -> str:
    """Return the API key or abort with a helpful message."""
    if api_key is not None:
        if not api_key:
            raise click.ClickException("API key cannot be empty.")
        return api_key

    key = get_api_key()
    if not key:
        raise click.ClickException(
            "No API key configured.\n"
            "  Run `schift auth login` or set the SCHIFT_API_KEY environment variable."
        )
    return key


def get_client(api_key: str | None = None) -> SchiftClient:
    """Create a client, ensuring an API key is present."""
    if api_key is None:
        ctx = click.get_current_context(silent=True)
        if ctx is not None and isinstance(ctx.obj, dict):
            api_key = ctx.obj.get("api_key")

    resolved_api_key = require_api_key(api_key)
    return SchiftClient(api_key=resolved_api_key)


def extract_items(data: Any, key: str) -> list[dict[str, Any]]:
    """Normalize list-like API responses."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def resolve_bucket(client: SchiftClient, bucket: str, *, create: bool = False) -> dict[str, Any]:
    buckets = extract_items(client.get("/buckets"), "buckets")
    for item in buckets:
        if item.get("id") == bucket or item.get("name") == bucket:
            return item

    if not create:
        raise click.ClickException(f"Bucket not found: {bucket}")

    created = client.post("/buckets", json={"name": bucket})
    if isinstance(created, dict) and isinstance(created.get("bucket"), dict):
        return created["bucket"]
    if isinstance(created, dict):
        return created
    raise click.ClickException("Unexpected create bucket response from Schift API.")
