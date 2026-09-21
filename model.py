from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from pydantic import BaseModel
from database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    hash_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user") # "admin", "landlord", "user"

class Listings(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False) # Apartment, Studio, Room
    location = Column(String, nullable=False)
    price = Column(Float, default=0.0)
    status = Column(String, default="available") # "available", "occupied"
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Applications(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String, nullable=False)
    status = Column(String, default="pending") # pending, accepted, rejected, cancelled



class ApplicationCreate(BaseModel):
    message: str


class RoommateRequests(Base):
    __tablename__ = "roommate_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    title = Column(String, nullable=False)        
    description = Column(String, nullable=False)  
    location = Column(String, nullable=False)  
    price = Column(Float, default=0.0)           
    status = Column(String, default="pending_approval") # pending_approval, approved, declined
