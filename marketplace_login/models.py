from typing import Literal

from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    seller_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    order_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    buyer_id: str = Field(min_length=1)
    buyer_phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class VerifyHandoff(BaseModel):
    buyer_phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    code: str = Field(pattern=r"^\d{4,8}$")


class OrderHandoff(BaseModel):
    order_id: str
    asset_id: str
    seller_id: str
    buyer_id: str
    status: Literal["awaiting_phone_verification", "ready_for_handoff"]


class OtpQueued(BaseModel):
    order_id: str
    status: Literal["awaiting_phone_verification"]
