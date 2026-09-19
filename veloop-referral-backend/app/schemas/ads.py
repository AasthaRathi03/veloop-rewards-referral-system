from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AdCompleteIn(BaseModel):
    """Client-side completion claim - still verified server side."""

    provider: str = Field("veloop-sdk", max_length=32)
    providerEventId: str = Field(min_length=8, max_length=128)
    adUnit: Optional[str] = Field(None, max_length=64)
    watchedSeconds: int = Field(ge=0, le=3600)
    completedAt: Optional[datetime] = None
    signature: Optional[str] = Field(None, max_length=128)


class AdPostbackIn(BaseModel):
    """Server-to-server postback from the ad provider (HMAC signed)."""

    provider: str = Field(max_length=32)
    providerEventId: str = Field(min_length=8, max_length=128)
    userId: str = Field(min_length=8, max_length=36)
    adUnit: Optional[str] = Field(None, max_length=64)
    watchedSeconds: int = Field(ge=0, le=3600)
    completedAt: Optional[datetime] = None
