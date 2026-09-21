import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base
from router.user import get_db, get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_housing.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return {"id": 1, "username": "testseeker", "role": "user"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """প্রতিটি টেস্ট রান করার আগে টেবিল তৈরি করবে এবং টেস্ট শেষে ডিলিট করে দেবে"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)



def test_request_roommate_listing_success():
    """ইউজার সফলভাবে রুমমেট রিকোয়েস্ট পাঠাতে পারছে কিনা তার টেস্ট"""
    payload = {
        "title": "Test Roommate Vacancy",
        "description": "Looking for a roommate in a test environment flat.",
        "location": "Sector 11, Uttara",
        "price": 8000.0
    }
    
  
    response = client.post("/user/Application_for_roommate", json=payload)
    
    assert response.status_code == 201
    assert response.json()["message"] == "Your roommate vacancy request has been submitted to admin for review."

def test_get_my_roommate_applications():
    """ইউজার তার নিজের পাঠানো রুমমেট রিকোয়েস্টের তালিকা দেখতে পারছে কিনা তার টেস্ট"""
 
    client.post("/user/Application_for_roommate", json={
        "title": "Temporary Flatmate",
        "description": "Short term roommate needed.",
        "location": "Mirpur",
        "price": 5000.0
    })
    
    
    response = client.get("/user/roommate_applications")
    
    assert response.status_code == 200
    assert "data" in response.json()
    assert response.json()["total_items"] == 1
