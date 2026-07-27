from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import certifi

USER_AGENT = "benchmark-radar/0.1 (+https://github.com/ktwu01/benchmark-radar)"


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    attempts: int = 3,
) -> Any:
    if params:
        clean = {key: value for key, value in params.items() if value is not None}
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    return json.loads(_request(url, request_headers, attempts).decode("utf-8"))


def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    attempts: int = 3,
) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    return _request(url, request_headers, attempts).decode("utf-8")


def _request(url: str, headers: dict[str, str], attempts: int) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers),
                timeout=30,
                context=ssl.create_default_context(cafile=certifi.where()),
            ) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error
