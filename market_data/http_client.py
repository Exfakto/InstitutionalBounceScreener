from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResponse:
    success: bool
    status_code: int | None = None
    data: object | None = None
    text: str | None = None
    error: str | None = None
    attempts: int = 0
    rate_limited: bool = False
    warnings: list[str] = field(default_factory=list)


class HttpClient:
    """
    Small injectable HTTP client with timeout, retries, 429 handling, and JSON parsing.
    """

    def __init__(
        self,
        opener=None,
        timeout=10,
        max_retries=3,
        rate_limit_sleep_seconds=1,
        sleeper=None,
    ):
        self.opener = opener or urlopen
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries or 0))
        self.rate_limit_sleep_seconds = max(0, float(rate_limit_sleep_seconds or 0))
        self.sleeper = sleeper or time.sleep

    def get_json(self, url, params=None, headers=None):
        query = urlencode(params or {})
        request_url = f"{url}?{query}" if query else url
        attempts = 0
        warnings = []

        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                request = Request(request_url, headers=headers or {})
                response = self.opener(request, timeout=self.timeout)
                status_code = getattr(response, "status", None) or getattr(response, "code", None) or 200
                payload = response.read().decode("utf-8")
                try:
                    parsed = json.loads(payload) if payload else None
                except json.JSONDecodeError as exc:
                    return HttpResponse(
                        False,
                        status_code=status_code,
                        text=payload,
                        error=f"Invalid JSON response: {exc}",
                        attempts=attempts,
                        warnings=warnings,
                    )
                return HttpResponse(
                    200 <= int(status_code) < 300,
                    status_code=status_code,
                    data=parsed,
                    text=payload,
                    attempts=attempts,
                    warnings=warnings,
                )
            except HTTPError as exc:
                status_code = exc.code
                if status_code == 429 and attempt < self.max_retries:
                    delay = self.backoff_seconds(attempt)
                    warnings.append(
                        f"Rate limit response received; retrying in {delay:g}s"
                    )
                    self.sleeper(delay)
                    continue
                if attempt < self.max_retries and status_code >= 500:
                    delay = self.backoff_seconds(attempt)
                    warnings.append(f"HTTP {status_code}; retrying in {delay:g}s")
                    self.sleeper(delay)
                    continue
                return HttpResponse(
                    False,
                    status_code=status_code,
                    error=f"HTTP {status_code}",
                    attempts=attempts,
                    rate_limited=status_code == 429,
                    warnings=warnings,
                )
            except (TimeoutError, URLError, OSError) as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_seconds(attempt)
                    warnings.append(f"Request failed; retrying in {delay:g}s: {exc}")
                    self.sleeper(delay)
                    continue
                return HttpResponse(
                    False,
                    error=str(exc),
                    attempts=attempts,
                    warnings=warnings,
                )

        return HttpResponse(False, error="Request failed", attempts=attempts, warnings=warnings)

    def backoff_seconds(self, attempt):
        return self.rate_limit_sleep_seconds * (2 ** attempt)
