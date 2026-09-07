from pydantic import BaseModel


class ReferralAttributeRequest(BaseModel):
    referral_code: str


class ReferralCreateRequest(BaseModel):
    referral_code: str
    referred_user_id: int


class LoginRequest(BaseModel):
    email: str
