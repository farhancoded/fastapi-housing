from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import Annotated
import model
from database import engine, SessionLocal
from router import admin, auth, user, listing
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Housing & Roommate Management Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shahriarhousing.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[
    Session,
    Depends(get_db)
]

app.include_router(listing.router)
app.include_router(auth.router,prefix="/auth",tags=["Authentication"])
app.include_router(admin.router,prefix="/admin",tags=["Admin Operations"])
app.include_router(user.router,prefix="/user",tags=["User Operations"])