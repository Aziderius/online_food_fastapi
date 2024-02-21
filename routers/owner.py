from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from .auth import get_current_user, validate_passwd, validate_phonenumber, validate_name, validate_last_name
from pydantic import BaseModel, Field
from models import Foods, Users, Restaurants, Categories, RestaurantRequests
from starlette import status
from passlib.context import CryptContext
from email_validator import validate_email


router = APIRouter(
    prefix='/owner',
    tags=['owner']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CreateUserRequest(BaseModel):
    first_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    email: str = Field(min_length=10)
    phonenumber:str
    password: str = Field(min_length=6)


class CreateRestaurantRequest(BaseModel):
    restaurant_name: str = Field(min_length=2)
    category_id: int = Field(gt=0)
    address: str = Field(min_length=10)
    rating: int = Field(gt=0, lt=6)


class CreateRequest(BaseModel):
    restaurant_id: int = Field(gt=0)
    restaurant_name: str = Field(min_length=2)
    category_id: int = Field(gt=0)
    address: str = Field(min_length=10)
    rating: int = Field(gt=0, lt=6)
    owner_id: int = Field(gt=0)


class CreateFoodRequest(BaseModel):
    food_name: str = Field(max_length=50)
    price: float = Field(gt=0)
    description: str = Field(max_length=200)


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
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).filter(Users.id == user.get("id")).first()


@router.get("/my-restaurants", status_code=status.HTTP_200_OK)
async def get_my_restaurants(user: user_dependency, db: db_dependency):
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    return db.query(Restaurants).filter(Restaurants.owner_id == user.get('id')).all()


@router.get("/menu/{restaurant_id}", status_code=status.HTTP_200_OK)
async def get_menu_by_restaurant_id(user: user_dependency, db:db_dependency, restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.owner_id == user.get('id')).first()

    food_model = db.query(Foods).filter(Foods.restaurant_id == restaurant_id).all()

    if not restaurant_model:
        raise HTTPException(status_code=403, detail='This restaurant does not belongs to you')
    
    return restaurant_model, food_model


@router.post("/new_restaurant", status_code=status.HTTP_201_CREATED)
async def create_restaurant(user: user_dependency,
                            db:db_dependency,
                            create_restaurant_request: CreateRestaurantRequest):
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    category_model = db.query(Categories).filter(Categories.id == create_restaurant_request.category_id).first()
    if not category_model:
        raise HTTPException(status_code=400, detail='invalid category')

    restaurant_model = Restaurants(
        restaurant_name=create_restaurant_request.restaurant_name,
        category_id=create_restaurant_request.category_id,
        address=create_restaurant_request.address,
        rating=create_restaurant_request.rating,
        owner_id=user.get("id")
    )

    db.add(restaurant_model)
    db.commit()

    return restaurant_model


@router.post("/restaurant/{restaurant_id}/new_food", status_code=status.HTTP_201_CREATED)
async def create_food(user: user_dependency,
                      db: db_dependency,
                      create_food_request: CreateFoodRequest,
                      restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id)\
        .filter(Restaurants.owner_id == user.get('id')).first()
    
    if not restaurant_model:
        raise HTTPException(status_code=404, detail='Restaurant not found or does not belong to the user')
    
    food_model = Foods(
        food_name = create_food_request.food_name,
        price = create_food_request.price,
        restaurant_id = restaurant_id,
        description = create_food_request.description
    )
    db.add(food_model)
    db.commit()

    return food_model


@router.put("/food/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def edit_food(user: user_dependency,
                    db: db_dependency,
                    create_food_request: CreateFoodRequest,
                    food_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if user.get("user_role") not in ['owner', 'admin']:
        raise HTTPException(status_code=403, detail='Permission Denied')
    
    food_model = db.query(Foods).filter(Foods.id == food_id).first()
    if not food_model:
        raise HTTPException(status_code=404, detail='Food not found')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == food_model.restaurant_id)\
    .filter(Restaurants.owner_id == user.get('id')).first()
    if not restaurant_model:
        raise HTTPException(status_code=404, detail='You are not allowed to update food from this restaurant')
    
    food_model.food_name = create_food_request.food_name
    food_model.price = create_food_request.price
    food_model.description = create_food_request.description
    
    db.commit()


@router.delete("/food/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(user: user_dependency, db: db_dependency, food_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if user.get("user_role") not in ['owner', 'admin']:
        raise HTTPException(status_code=403, detail='Permission Denied')
    
    food_model = db.query(Foods).filter(Foods.id == food_id).first()
    if not food_model:
        raise HTTPException(status_code=404, detail='Food not found')
    
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == food_model.restaurant_id)\
    .filter(Restaurants.owner_id == user.get('id')).first()
    if not restaurant_model:
        raise HTTPException(status_code=403, detail='You are not allowed to delete food from this restaurant')
    
    db.query(Foods).filter(Foods.id == food_id).delete()
    db.commit()


@router.post("/create_owner", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
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
        role = "owner"
    )
    db.add(create_user_model)
    db.commit()
    

@router.post("/request_restaurant/{restaurant_id}", status_code=status.HTTP_201_CREATED)
async def request_to_change_restaurant_info(user: user_dependency,
                                                db: db_dependency,
                                                create_request: CreateRequest,
                                                restaurant_id: int = Path(gt=0)):
    if user is None or user.get("user_role") != 'owner':
        raise HTTPException(status_code=401, detail='Authentication Failed')
        
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id)\
    .filter(Restaurants.owner_id == user.get("id"))

    if not restaurant_model:
        raise HTTPException(status_code=404, detail='Restaurant not found or does not belong to the user')
        
    request_model = RestaurantRequests(**create_request.model_dump())

    db.add(request_model)
    db.commit()