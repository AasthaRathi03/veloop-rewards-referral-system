from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import ReferralAttributeRequest, ReferralCreateRequest
from auth import get_current_user
from schemas import ReferralAttributeRequest, ReferralCreateRequest, LoginRequest
from auth import get_current_user, create_access_token

from database import get_db
from models import User, Referral

router = APIRouter(prefix="/api/referrals", tags=["Referrals"])


@router.post("/attribute")
def attribute_referral(data: ReferralAttributeRequest, db: Session = Depends(get_db)):
    # Referral code se referrer user find karo
    referrer = db.query(User).filter(User.referral_code == data.referral_code).first()

    # Agar referral code galat hai
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    return {
        "message": "Referral code is valid",
        "referrer_user_id": referrer.id,
        "referral_code": referrer.referral_code,
    }


@router.post("/create")
def create_referral(data: ReferralCreateRequest, db: Session = Depends(get_db)):
    # Find the referrer using the referral code
    referrer = db.query(User).filter(User.referral_code == data.referral_code).first()

    # Check if the referral code is valid
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    # Check if the referred user exists
    referred_user = db.query(User).filter(User.id == data.referred_user_id).first()

    # Return an error if the referred user does not exist
    if not referred_user:
        raise HTTPException(status_code=404, detail="Referred user not found")

    # Prevent self-referral
    if referrer.id == referred_user.id:
        raise HTTPException(status_code=400, detail="Self referral is not allowed")

    # Check whether the referred user already has a referral
    existing_referral = (
        db.query(Referral).filter(Referral.referred_user_id == referred_user.id).first()
    )

    # Prevent multiple referrals for the same user
    if existing_referral:
        raise HTTPException(status_code=400, detail="User already has a referral")

    # Create a new referral record
    referral = Referral(
        referrer_user_id=referrer.id,
        referred_user_id=referred_user.id,
        referral_code=data.referral_code,
        status="PENDING",
        attribution_source="referral_link",
    )

    # Add the referral record to the database
    db.add(referral)

    # Save the changes
    db.commit()

    # Refresh the object to get the generated referral ID
    db.refresh(referral)

    return {
        "message": "Referral created successfully",
        "referral_id": referral.id,
        "status": referral.status,
    }


@router.get("/me")
def get_my_referrals(
    db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)
):
    referrals = (
        db.query(Referral).filter(Referral.referrer_user_id == current_user_id).all()
    )

    return {
        "total_referrals": len(referrals),
        "referrals": [
            {
                "referral_id": referral.id,
                "referred_user_id": referral.referred_user_id,
                "status": referral.status,
                "created_at": referral.created_at,
            }
            for referral in referrals
        ],
    }


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Find the user by email
    user = db.query(User).filter(User.email == data.email).first()

    # Check if the user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate an access token for the user
    access_token = create_access_token(user.id)

    return {"access_token": access_token, "token_type": "bearer"}
