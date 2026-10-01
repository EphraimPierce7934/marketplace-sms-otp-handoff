import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .handoff_service import CodeNotVerified, HandoffNotFound, MarketplaceHandoffService, PhoneMismatch
from .infrai_sms import InfraiError, InfraiSms
from .models import BuyerUpdate, OrderHandoff, OtpQueued, SellerAsset, VerifyHandoff


def create_app(service: MarketplaceHandoffService | None = None) -> FastAPI:
    owned_sms: InfraiSms | None = None
    if service is None:
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        owned_sms = InfraiSms(api_key)
        service = MarketplaceHandoffService(owned_sms)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if owned_sms is not None:
            await owned_sms.close()

    app = FastAPI(title="Marketplace SMS handoff", lifespan=lifespan)

    @app.exception_handler(InfraiError)
    async def infrai_rejection(_, exc: InfraiError):
        from fastapi.responses import JSONResponse

        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        return JSONResponse(status_code=status, content={"detail": exc.code})

    @app.post("/seller-assets", response_model=SellerAsset, status_code=201)
    async def add_asset(asset: SellerAsset) -> SellerAsset:
        return service.add_asset(asset)

    @app.post("/buyer-updates", response_model=OtpQueued, status_code=202)
    async def buyer_update(update: BuyerUpdate) -> OtpQueued:
        try:
            return await service.start_buyer_login(update)
        except HandoffNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/orders/{order_id}/handoff", response_model=OrderHandoff)
    async def verify_handoff(order_id: str, request: VerifyHandoff) -> OrderHandoff:
        try:
            return await service.verify_and_release(order_id, request)
        except HandoffNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PhoneMismatch as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CodeNotVerified as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    return app


app = create_app()
