import json

import httpx
import pytest

from marketplace_login.infrai_sms import InfraiError, InfraiSms


@pytest.mark.asyncio
async def test_business_rejection_is_read_from_envelope() -> None:
    async def reject(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/sms/verify"
        assert json.loads(request.content) == {
            "to": "+15551234567",
            "code": "481205",
            "idempotency_key": "order-9-verify",
        }
        return httpx.Response(400, json={"ok": False, "data": None, "error": {"code": "denied"}})

    client = InfraiSms("test-key", transport=httpx.MockTransport(reject))
    with pytest.raises(InfraiError) as caught:
        await client.verify_otp("+15551234567", "481205", "order-9-verify")
    assert caught.value.status_code == 400
    assert caught.value.code == "denied"
    await client.close()
