from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from database import SessionLocal
from model import Users, Listings, Applications, RoommateRequests # ফিক্সড: RoommateRequests ইম্পোর্ট করা হলো
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from router.auth import get_current_user

router = APIRouter(tags=["Admin Operations"])


class ListingCreate(BaseModel):
    title: str
    description: str
    category: str  # "Apartment", "Studio", "Shared Room"
    location: str
    price: float = Field(default=0.0, ge=0)
    image_url: Optional[str] = None 

class ListingUpdate(BaseModel):
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    price: Optional[float] = Field(default=None)
    status: Optional[str] = Field(default=None)  # "available" or "occupied"
    image_url: Optional[str] = Field(default=None) 

class ApplicationApproval(BaseModel):
    application_id: int
    action: str = Field(description="Must be 'approve' / 'accepted' or 'reject' / 'rejected'")

class RoommateAction(BaseModel):
    request_id: int
    action: str = Field(description="Must be 'approve' or 'decline'")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post('/create_listing')
def create_listing(user: user_dependency, db: db_dependency, new_listing: ListingCreate):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    listing_model = Listings(
        **new_listing.model_dump(),
        status="available",
        owner_id=user.get('id'),
        created_at=datetime.now(timezone.utc)
    )

    db.add(listing_model)
    db.commit()
    return JSONResponse(status_code=201, content={'message': 'Listing added successfully'})


@router.put('/update_listing/{listing_id}')
def update_listing(user: user_dependency, db: db_dependency, update_data: ListingUpdate, listing_id: int):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    listing = db.query(Listings).filter(Listings.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail='Listing not found')

    dumped_data = update_data.model_dump(exclude_unset=True)

    for key, value in dumped_data.items():
        setattr(listing, key, value)
    
    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Listing updated successfully'})


@router.delete('/delete_listing/{listing_id}')
def delete_listing(user: user_dependency, db: db_dependency, listing_id: int):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    listing = db.query(Listings).filter(Listings.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail='Listing not found')

    db.query(Listings).filter(Listings.id == listing_id).delete()
    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Listing deleted successfully'})


@router.get('/applications')
def get_all_applications(user: user_dependency, db: db_dependency):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')
        
    applications = db.query(Applications).all()
    return applications


@router.post('/approve_application')
def approve_application(user: user_dependency, db: db_dependency, approval_request: ApplicationApproval):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    application = db.query(Applications).filter(Applications.id == approval_request.application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail='Application record not found')

    listing = db.query(Listings).filter(Listings.id == application.listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail='Associated listing not found')

    action_lower = approval_request.action.lower()


    if action_lower in ['accepted', 'approve', 'approved']:
        if listing.status == 'occupied':
            raise HTTPException(status_code=400, detail='This property is already occupied')
        
        application.status = 'accepted'
        listing.status = 'occupied' 
        final_status = 'accepted'
    elif action_lower in ['rejected', 'reject', 'decline', 'declined']:
        application.status = 'rejected'
        final_status = 'rejected'
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'.")

    db.commit()
    return JSONResponse(
        status_code=200, 
        content={'message': f'Application status successfully set to {final_status}'}
    )


@router.put('/release_listing/{listing_id}')
def release_listing(user: user_dependency, db: db_dependency, listing_id: int):
    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=401, detail='Failed Authentication')

    listing = db.query(Listings).filter(Listings.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail='Listing not found')

    listing.status = 'available'

    db.commit()
    return JSONResponse(status_code=200, content={'message': 'Listing status marked back to available'})


@router.get("/roommate_requests")
def get_roommate_requests(
    user: user_dependency,
    db: db_dependency
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed Authentication"
        )

    requests = db.query(RoommateRequests).all()

    return requests


@router.post("/review_roommate_request")
def review_roommate_request(
    user: user_dependency,
    db: db_dependency,
    review: RoommateAction
):
    if user is None or user.get("role") != "admin":
        raise HTTPException(
            status_code=401,
            detail="Failed Authentication"
        )

    req = db.query(RoommateRequests).filter(
        RoommateRequests.id == review.request_id
    ).first()

    if not req:
        raise HTTPException(
            status_code=404,
            detail="Roommate request record not found"
        )

    action_lower = review.action.lower()

    if action_lower not in ["approve", "decline"]:
        raise HTTPException(
            status_code=400,
            detail="Action must be 'approve' or 'decline'"
        )

    if action_lower == "approve":

        # Change roommate request status
        req.status = "approved"

        # Create a listing from the roommate request
        approved_listing = Listings(
            title=req.title,
            description=req.description,
            category="Shared Room",
            location=req.location,
            price=req.price,
            status="available",
            owner_id=req.user_id,
            image_url=""
        )

        db.add(approved_listing)

    else:

        # Decline roommate request
        req.status = "declined"

    db.commit()

    return {
        "message": (
            f"Roommate request has been successfully "
            f"{action_lower}d."
        )
    }