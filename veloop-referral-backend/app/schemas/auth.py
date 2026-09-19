import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

CODE_RE = re.compile(r"^[A-Z0-9]{4,16}$")


class DeviceSignalsIn(BaseModel):
    """Minimal, privacy-conscious device signals collected by the frontend."""

    platform: str = Field("", max_length=64)
    screen: str = Field("", max_length=32)
    timezone: str = Field("", max_length=64)
    language: str = Field("", max_length=16)
    hardware: str = Field("", max_length=32)
    canvasHint: str = Field("", max_length=64)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    referralCode: Optional[str] = Field(None, max_length=16)

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, v):
           if v is None or (isinstance(v, str) and v.strip() == ""):
               return None
           v = v.strip()
           if not re.match(r"^\+?[0-9]{8,15}$", v):
               raise ValueError("Phone number format is invalid")
           return v

    @field_validator("referralCode")
    @classmethod
    def _code(cls, v):
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if not CODE_RE.match(v):
            raise ValueError("Referral code format is invalid")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    referralCode: str
    level: int
    balances: dict


class AuthOut(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    deviceToken: str
    user: UserOut
    referral: Optional[dict] = None
