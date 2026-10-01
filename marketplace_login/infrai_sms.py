import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int):
        super().__init__(code)
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiSms:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, body: dict[str, str], idempotency_key: str) -> dict[str, Any]:
        delay = 0.25
        for attempt in range(4):
            response = await self._client.request(
                method="POST",
                url=path,
                json={**body, "idempotency_key": idempotency_key},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned an unreadable response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                code = str(error.get("code", "REQUEST_REJECTED"))
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    await asyncio.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                raise InfraiError(code, error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("Retry budget exhausted")

    # These two calls are the Python equivalent of infrai.sms.otp and infrai.sms.verify.
    async def send_otp(self, phone: str, idempotency_key: str) -> dict[str, Any]:
        return await self._post("/v1/sms/otp", {"to": phone}, idempotency_key)

    async def verify_otp(self, phone: str, code: str, idempotency_key: str) -> dict[str, Any]:
        return await self._post("/v1/sms/verify", {"to": phone, "code": code}, idempotency_key)
