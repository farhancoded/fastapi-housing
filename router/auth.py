from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from database import SessionLocal
from model import Users 
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError

router = APIRouter(tags=["Authentication"])

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

OAuth2_bearer = OAuth2PasswordBearer(tokenUrl='/auth/login')

SECRET_KEY ='86746eeb8285ca279c6251e0bd83cdd50c88027b934a93f19d8b9af782139516'
ALGORITHM = 'HS256' 


class CreateUsers(BaseModel):
    email : EmailStr  
    username : str
    firstname : str
    lastname : str
    password : str
    role : str = "user" 

class UpdateUser(BaseModel):
    email : Optional[EmailStr] = Field(default=None)
    username : Optional[str] = Field(default=None)
    firstname : Optional[str] = Field(default=None)
    lastname : Optional[str]= Field(default=None)

class UpdatePassword(BaseModel):
    current_password : str
    new_password: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


def authenticate_user(username, password, db):
    user = db.query(Users).filter(Users.username == username).first()
    if user is None:
        return False
    if bcrypt_context.verify(password, user.hash_password):
        return user
    return False


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta, token_type: str = "access"):
    encode = {'sub': username, 'id': user_id, 'role': role, 'token_type': token_type}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(OAuth2_bearer)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") == "refresh":
            raise credentials_exception
            
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        role: str = payload.get('role')
        if username is None or user_id is None:
            raise credentials_exception
        return {'username': username, 'id': user_id, 'role': role}
    except JWTError:
        raise credentials_exception


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post('/createuser', status_code=status.HTTP_201_CREATED)
def create_users(db : db_dependency, new_user : CreateUsers):
    existing_username = db.query(Users).filter(Users.username == new_user.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail='Username already exists')

    existing_email = db.query(Users).filter(Users.email == new_user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail='Email already exists')

    user_model = Users(
        email = new_user.email,
        username = new_user.username,
        firstname = new_user.firstname,
        lastname = new_user.lastname,
        hash_password = bcrypt_context.hash(new_user.password),
        is_active = True,
        role = new_user.role
    )

    db.add(user_model)
    db.commit()

    return JSONResponse(status_code=201, content={'message' : 'User created successfully'})

@router.post('/login')
def login_user(db : db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password, db) 
    
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password"
        )

    access_token = create_access_token(user.username, user.id, user.role, timedelta(minutes=30), token_type="access")
    refresh_token = create_access_token(user.username, user.id, user.role, timedelta(days=7), token_type="refresh")
    
    return {
        'access_token': access_token, 
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }


@router.put('/edituser')
def update_user(user: user_dependency, db : db_dependency, update_user : UpdateUser):
    if user is None: 
        raise HTTPException(status_code=401, detail='Failed Authentication')
    
    db_user = db.query(Users).filter(Users.id == user.get('id')).first()
    if db_user is None:
        raise HTTPException(status_code=44, detail='User not found')
        
    update_data = update_user.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    return JSONResponse(status_code=200, content={'message' : 'User updated successfully'})


@router.put('/passwordchange')
def update_password(user: user_dependency, db : db_dependency, update_password : UpdatePassword):
    if user is None: 
        raise HTTPException(status_code=401, detail='Failed Authentication')
    
    db_user = db.query(Users).filter(Users.id == user.get('id')).first()
    
    if not bcrypt_context.verify(update_password.current_password, db_user.hash_password):
        raise HTTPException(status_code=401, detail='Wrong Password')

    db_user.hash_password = bcrypt_context.hash(update_password.new_password)

    db.commit()
    return JSONResponse(status_code=200, content={'message' : 'Password updated successfully'})


@router.get('/user')
def get_user_details(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')
    
    current_user = db.query(Users).filter(Users.id == user.get('id')).first()
    if current_user is None:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'firstname': current_user.firstname,
        'lastname': current_user.lastname,
        'role': current_user.role,
        'is_active': current_user.is_active
    }



@router.post("/refresh", status_code=status.HTTP_200_OK,include_in_schema=False)
def refresh_access_token(request: TokenRefreshRequest, db: db_dependency):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")
            
        user = db.query(Users).filter(Users.username == username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
            
  
        new_access_token = create_access_token(
            username=user.username, user_id=user.id, role=user.role, 
            expires_delta=timedelta(minutes=30), token_type="access"
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired or is invalid")


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(request: ForgotPasswordRequest, db: db_dependency):
    user = db.query(Users).filter(Users.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account registered with this email address")

    temporary_password = "ResetSecurePass123!"
    user.hash_password = bcrypt_context.hash(temporary_password)
    db.commit()
    
    return {
        "message": "A temporary password has been successfully generated for your account.",
        "temporary_password": temporary_password,
        "note": "Please login using this temporary password and change it immediately from your profile settings."
    }
