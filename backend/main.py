from fastapi import FastAPI
from routes.referrals import router as referral_router

from database import engine, Base
import models

app = FastAPI(title="VELOOP Rewards Backend")
app.include_router(referral_router)


Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    try:
        with engine.connect():
            return {"message": "VELOOP Backend + PostgreSQL connected successfully"}
    except Exception as e:
        return {"error": str(e)}
