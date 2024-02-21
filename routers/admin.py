from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from .auth import get_current_user, validate_passwd, validate_phonenumber, validate_name, validate_last_name
from pydantic import BaseModel, Field
from models import Foods, Users, Restaurants, RestaurantRequests, PurchaseRecords
from starlette import status
from passlib.context import CryptContext
from email_validator import validate_email


router = APIRouter(
    prefix='/admin',
    tags=['admin']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UpdateRestaurant(BaseModel):
    restaurant_name: str = Field(min_length=2)
    category_id: int = Field(gt=0)
    address: str = Field(min_length=10)
    rating: int = Field(gt=0, lt=6)
    owner_id: int = Field(gt=0)


class CreateUserRequest(BaseModel):
    first_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    email: str = Field(min_length=10)
    phonenumber:str
    password: str = Field(min_length=6)


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


@router.get("/users", status_code=status.HTTP_200_OK)
async def get_all_users(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(Users).all()


@router.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def get_user_by_id(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    user_model = db.query(Users).filter(Users.id == user_id).first()

    if not user_model:
        raise HTTPException(status_code=404, detail='User not found')
    
    return user_model


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    user_model = db.query(Users).filter(Users.id == user_id).first()

    if not user_model:
        raise HTTPException(status_code=404, detail='User not found')
    
    db.query(Users).filter(Users.id == user_id).delete()
    db.commit()


@router.get("/purchase_record", status_code=status.HTTP_200_OK)
async def get_purchase_records(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(PurchaseRecords).all()


@router.get("/purchase_record/user/{user_id}")
async def get_purchase_record_by_user_id(user: user_dependency, db: db_dependency, user_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    user_model = db.query(PurchaseRecords).filter(PurchaseRecords.user_id == user_id).all()

    if not user :
        raise HTTPException(status_code=404, detail='User not found')
    
    return user_model


@router.get("/requests", status_code=status.HTTP_200_OK)
async def get_requests_undone(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    request_model = db.query(RestaurantRequests).filter(RestaurantRequests.request_done == False).all()

    requests = []
    for request in request_model:
        requests.append({
            "restaurant_id": request.restaurant_id,
            "restaurant_name": request.restaurant_name,
            "category_id": request.category_id,
            "address": request.address,
            "rating": request.rating,
            "owner_id": request.owner_id
        })
    return requests


@router.get("/requests_done", status_code=status.HTTP_200_OK)
async def get_all_requests(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(RestaurantRequests).all()


@router.get("/restaurant/{restaurant_id}", status_code=status.HTTP_200_OK)
async def get_restaurant_by_id(user: user_dependency, db: db_dependency, restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id).first()

    if not restaurant_model:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    
    return restaurant_model


@router.put("/restaurant/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_restaurant_info(user: user_dependency,
                                 db: db_dependency,
                                 update_restaurant: UpdateRestaurant,
                                 restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id).first()

    if not restaurant_model:
        raise HTTPException(status_code=404, detail='Restaurant not found')
   
    restaurant_model.restaurant_name = update_restaurant.restaurant_name
    restaurant_model.category_id = update_restaurant.category_id
    restaurant_model.address = update_restaurant.address
    restaurant_model.rating = update_restaurant.rating
    restaurant_model.owner_id = update_restaurant.owner_id

    request_model = db.query(RestaurantRequests).filter(RestaurantRequests.restaurant_id == restaurant_id).first()
    if request_model:
        request_model.request_done = True

    db.commit()


@router.delete("/delete_restaurant/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_restaurant(user: user_dependency, db: db_dependency, restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'admin':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id).first()

    if not restaurant_model:
        raise HTTPException(status_code=404, detail='Restaurant not found')
    
    db.query(RestaurantRequests).filter(RestaurantRequests.restaurant_id == restaurant_id).delete()
    db.query(Foods).filter(Foods.restaurant_id == restaurant_id).delete()
    db.query(Restaurants).filter(Restaurants.id == restaurant_id).delete()

    db.commit()
    

@router.post("/create_admin", status_code=status.HTTP_201_CREATED)
async def create_admin_user(db: db_dependency, create_user_request: CreateUserRequest):
    if not validate_name(create_user_request.first_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='First name must contain letters')
    
    if not validate_last_name(create_user_request.last_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Last name must contain letters')
    
    if not validate_email(create_user_request.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The Email is not valid')
    
    if not validate_phonenumber(create_user_request.phonenumber):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Phonenumber is not valid')
    
    if not validate_passwd(create_user_request.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must have at least one uppercase, one lowercase, one digit, one symbol, and be at least 6 characters long."
        )
    
    create_user_model = Users(
        first_name = create_user_request.first_name,
        last_name = create_user_request.last_name,
        email = create_user_request.email,
        phonenumber = create_user_request.phonenumber,
        hashed_password = bcrypt_context.hash(create_user_request.password),
        role = "admin"
    )
    db.add(create_user_model)
    db.commit()
