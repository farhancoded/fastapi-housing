from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date
from typing import Annotated, Optional
from datetime import date
from database import SessionLocal
from model import Listings


router = APIRouter(tags=["Listing Operations"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/listings")
def get_all_listings(
    db: Annotated[Session, Depends(get_db)],
    search: Optional[str] = Query(None, description="Search by title or description"),
    listing_id: Optional[int] = Query(None, description="Search exactly by Listing ID"), 
    category: Optional[str] = Query(None, description="Filter by room category"),
    location: Optional[str] = Query(None, description="Filter by location"),
    status: Optional[str] = Query(None, description="Filter by status (available/occupied)"),

    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
 
    sort_by: Optional[str] = Query("newest", description="newest, alphabetical, price_asc, price_desc"),

    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, description="Number of items per page")
):
    query = db.query(Listings)

    if listing_id:
        query = query.filter(Listings.id == listing_id)

    if status:
        query = query.filter(Listings.status == status)
    else:
        query = query.filter(Listings.status == "available")

    if search:
        query = query.filter(
            (Listings.title.ilike(f"%{search}%")) |
            (Listings.description.ilike(f"%{search}%"))
        )

    if category:
        query = query.filter(Listings.category.ilike(f"%{category}%"))
    if location:
        query = query.filter(Listings.location.ilike(f"%{location}%"))

    if start_date:
        query = query.filter(cast(Listings.created_at, Date) >= start_date)
    if end_date:
        query = query.filter(cast(Listings.created_at, Date) <= end_date)

    if sort_by == "price_asc":
        query = query.order_by(Listings.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Listings.price.desc())
    elif sort_by == "alphabetical":
        query = query.order_by(Listings.title.asc()) 
    else:
        query = query.order_by(Listings.created_at.desc())

    total_count = query.count()
    offset = (page - 1) * limit
    listings = query.offset(offset).limit(limit).all()

    return {
        "total_items": total_count,
        "page": page,
        "limit": limit,
        "data": listings
    }


@router.get("/listings/{listing_id}")
def get_specific_listing(listing_id: int, db: Annotated[Session, Depends(get_db)]):
    listing = db.query(Listings).filter(Listings.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing
