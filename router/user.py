from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from database import SessionLocal
from model import Listings, Applications, RoommateRequests
from router.auth import get_current_user
from fastapi.responses import JSONResponse

router = APIRouter(tags=["User Operations"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ApplicationRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Message to the admin/room owner"
    )


class RoommateRequestCreate(BaseModel):
    title: str
    description: str
    location: str
    price: float = Field(..., ge=0)
    image_url: Optional[str] = None



@router.post("/apply/{listing_id}", status_code=status.HTTP_201_CREATED)
def apply_for_room(
    listing_id: int, 
    request_body: ApplicationRequest, 
    user: user_dependency,
    db: db_dependency
):
    if user is None or user.get("role") != "user":
        raise HTTPException(status_code=401, detail="Only authenticated room seekers can apply")

    listing = db.query(Listings).filter(Listings.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.status != "available":
        raise HTTPException(status_code=400, detail="This listing is no longer available")

    existing_application = db.query(Applications).filter(
        Applications.listing_id == listing_id,
        Applications.user_id == user.get("id"),
        Applications.status != "rejected"
    ).first()

    if existing_application:
        raise HTTPException(status_code=400, detail="You have already applied for this listing")

    application = Applications(
        listing_id=listing_id,
        user_id=user.get("id"),
        message=request_body.message,
        status="pending"
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return JSONResponse(
        status_code=201,
        content={
            "message": "Application submitted successfully",
            "application_id": application.id,
            "status": "pending"
        }
    )


@router.get("/applications")
def get_my_applications(user: user_dependency, db: db_dependency):
    if user is None or user.get("role") != "user":
        raise HTTPException(status_code=401, detail="Unauthorized access")
        
    applications = db.query(Applications).filter(
        Applications.user_id == user.get("id")
    ).order_by(Applications.id.desc()).all()

    return {
        "total_items": len(applications),
        "data": applications
    }


@router.post("/Application_for_roommate", status_code=status.HTTP_201_CREATED)
def request_roommate_listing(
    request_data: RoommateRequestCreate, 
    user: user_dependency, 
    db: db_dependency
):
    if user is None or user.get("role") != "user":
        raise HTTPException(status_code=401, detail="Only authenticated room seekers can request a roommate listing")

    new_request = RoommateRequests(
        user_id=user.get("id"),
        title=request_data.title,
        description=request_data.description,
        location=request_data.location,
        price=request_data.price,
        status="pending_approval"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return {"message": "Your roommate vacancy request has been submitted to admin for review."}


@router.get("/roommate_applications")
def get_my_roommate_requests(user: user_dependency, db: db_dependency):
    if user is None or user.get("role") != "user":
        raise HTTPException(status_code=401, detail="Unauthorized access")
        
  
    my_roommate_apps = db.query(RoommateRequests).filter(
        RoommateRequests.user_id == user.get("id")
    ).order_by(RoommateRequests.id.desc()).all()

    return {
        "total_items": len(my_roommate_apps),
        "data": my_roommate_apps
    }
