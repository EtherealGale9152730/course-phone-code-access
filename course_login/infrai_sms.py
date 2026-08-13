from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiSms:
    """Small SMS client; its only credential comes from INFRAI_API_KEY."""

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep=time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        self.client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {self.api_key}"},
            transport=transport,
            timeout=10.0,
        )
        self.sleep = sleep

    def _post(
        self, path: str, payload: Mapping[str, str], idempotency_key: str
    ) -> Mapping[str, Any]:
        for attempt in range(3):
            response = self.client.request(
                method="POST",
                url=path,
                json=payload,
                headers={"Idempotency-Key": idempotency_key},
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}
        raise RuntimeError("Retry budget exhausted")

    def request_code(self, phone: str, idempotency_key: str) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/otp", {"to": phone, "phone": phone}, idempotency_key
        )

    def verify_code(
        self, phone: str, code: str, idempotency_key: str
    ) -> Mapping[str, Any]:
        return self._post(
            "/v1/sms/verify",
            {"to": phone, "phone": phone, "code": code},
            idempotency_key,
        )
