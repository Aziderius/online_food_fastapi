from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Annotated
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal
from .auth import get_current_user, validate_passwd, validate_phonenumber
from pydantic import BaseModel, Field
from models import ShoppingCart, Foods, Users, PurchaseRecords, Restaurants
from starlette import status
from passlib.context import CryptContext
from email_validator import validate_email


router = APIRouter(
    prefix='/user',
    tags=['user']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phonenumber:str
    password: str
    role: str


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6)


class EmailVerification(BaseModel):
    email: str
    new_email: str


class PhoneNumberVerification(BaseModel):
    phonenumber: str
    new_phonenumber: str


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


@router.get("/", status_code=status.HTTP_200_OK)
async def get_owner_user(user: user_dependency, db:db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).filter(Users.id == user.get("id")).first()