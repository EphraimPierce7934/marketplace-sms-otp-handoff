from typing import Any

import pytest

from marketplace_login.handoff_service import CodeNotVerified, MarketplaceHandoffService
from marketplace_login.models import BuyerUpdate, SellerAsset, VerifyHandoff


class FakeSms:
    def __init__(self, verified: bool):
        self.verified = verified
        self.sent_to: list[str] = []

    async def send_otp(self, phone: str, idempotency_key: str) -> dict[str, Any]:
        self.sent_to.append(phone)
        return {"message_id": "msg-1"}

    async def verify_otp(self, phone: str, code: str, idempotency_key: str) -> dict[str, Any]:
        return {"verified": self.verified}


def seeded_service(sms: FakeSms) -> MarketplaceHandoffService:
    service = MarketplaceHandoffService(sms)  # type: ignore[arg-type]
    service.add_asset(SellerAsset(asset_id="asset-7", seller_id="seller-2", title="Launch kit"))
    return service


@pytest.mark.asyncio
async def test_verified_buyer_unlocks_order_handoff() -> None:
    sms = FakeSms(verified=True)
    service = seeded_service(sms)
    await service.start_buyer_login(
        BuyerUpdate(order_id="order-9", asset_id="asset-7", buyer_id="buyer-4", buyer_phone="+15551234567")
    )

    result = await service.verify_and_release(
        "order-9", VerifyHandoff(buyer_phone="+15551234567", code="481205")
    )

    assert sms.sent_to == ["+15551234567"]
    assert result.status == "ready_for_handoff"
    assert result.seller_id == "seller-2"


@pytest.mark.asyncio
async def test_unverified_code_keeps_handoff_closed() -> None:
    service = seeded_service(FakeSms(verified=False))
    await service.start_buyer_login(
        BuyerUpdate(order_id="order-9", asset_id="asset-7", buyer_id="buyer-4", buyer_phone="+15551234567")
    )

    with pytest.raises(CodeNotVerified):
        await service.verify_and_release(
            "order-9", VerifyHandoff(buyer_phone="+15551234567", code="481205")
        )

    assert service.orders["order-9"].status == "awaiting_phone_verification"
