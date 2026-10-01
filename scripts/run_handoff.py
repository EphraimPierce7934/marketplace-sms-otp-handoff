import asyncio
import os

from marketplace_login.handoff_service import MarketplaceHandoffService
from marketplace_login.infrai_sms import InfraiSms
from marketplace_login.models import BuyerUpdate, SellerAsset, VerifyHandoff


async def main() -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    phone = os.environ.get("BUYER_PHONE")
    if not api_key or not phone:
        raise RuntimeError("INFRAI_API_KEY and BUYER_PHONE are required")

    sms = InfraiSms(api_key)
    service = MarketplaceHandoffService(sms)
    service.add_asset(SellerAsset(asset_id="theme-204", seller_id="seller-8", title="Storefront theme"))
    queued = await service.start_buyer_login(
        BuyerUpdate(order_id="order-1042", asset_id="theme-204", buyer_id="buyer-31", buyer_phone=phone)
    )
    print(queued.model_dump_json())
    code = input("SMS code: ").strip()
    handoff = await service.verify_and_release("order-1042", VerifyHandoff(buyer_phone=phone, code=code))
    print(handoff.model_dump_json())
    await sms.close()


if __name__ == "__main__":
    asyncio.run(main())
