from hashlib import sha256

from .infrai_sms import InfraiSms
from .models import BuyerUpdate, OrderHandoff, OtpQueued, SellerAsset, VerifyHandoff


class HandoffNotFound(Exception):
    pass


class PhoneMismatch(Exception):
    pass


class CodeNotVerified(Exception):
    pass


class MarketplaceHandoffService:
    def __init__(self, sms: InfraiSms):
        self.sms = sms
        self.assets: dict[str, SellerAsset] = {}
        self.orders: dict[str, OrderHandoff] = {}
        self.phones: dict[str, str] = {}

    def add_asset(self, asset: SellerAsset) -> SellerAsset:
        self.assets[asset.asset_id] = asset
        return asset

    async def start_buyer_login(self, update: BuyerUpdate) -> OtpQueued:
        asset = self.assets.get(update.asset_id)
        if asset is None:
            raise HandoffNotFound("seller asset was not found")
        handoff = OrderHandoff(
            order_id=update.order_id,
            asset_id=asset.asset_id,
            seller_id=asset.seller_id,
            buyer_id=update.buyer_id,
            status="awaiting_phone_verification",
        )
        await self.sms.send_otp(update.buyer_phone, self._key("send", update.order_id, update.buyer_phone))
        self.orders[update.order_id] = handoff
        self.phones[update.order_id] = update.buyer_phone
        return OtpQueued(order_id=update.order_id, status="awaiting_phone_verification")

    async def verify_and_release(self, order_id: str, request: VerifyHandoff) -> OrderHandoff:
        handoff = self.orders.get(order_id)
        if handoff is None:
            raise HandoffNotFound("order handoff was not found")
        if self.phones[order_id] != request.buyer_phone:
            raise PhoneMismatch("phone does not match this order")
        result = await self.sms.verify_otp(
            request.buyer_phone,
            request.code,
            self._key("verify", order_id, request.buyer_phone, request.code),
        )
        if result.get("verified") is not True:
            raise CodeNotVerified("phone code was not verified")
        released = handoff.model_copy(update={"status": "ready_for_handoff"})
        self.orders[order_id] = released
        return released

    @staticmethod
    def _key(*parts: str) -> str:
        return sha256(":".join(parts).encode()).hexdigest()
