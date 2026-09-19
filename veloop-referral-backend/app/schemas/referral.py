import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

CODE_RE = re.compile(r"^[A-Z0-9]{4,16}$")


class AttributeIn(BaseModel):
    referralCode: str = Field(min_length=4, max_length=16)
    source: str = Field("LINK", max_length=32)

    @field_validator("referralCode")
    @classmethod
    def _code(cls, v):
        v = v.strip().upper()
        if not CODE_RE.match(v):
            raise ValueError("Referral code format is invalid")
        return v


class ClickIn(BaseModel):
    referralCode: str = Field(min_length=4, max_length=16)

    @field_validator("referralCode")
    @classmethod
    def _code(cls, v):
        return v.strip().upper()


class ReferralListQuery(BaseModel):
    page: int = Field(1, ge=1, le=10_000)
    limit: int = Field(20, ge=1, le=100)
    status: Optional[str] = Field(None, max_length=16)


class AdminStatusIn(BaseModel):
    status: str = Field(max_length=20)
    reason: str = Field(max_length=200)
