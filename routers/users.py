from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Annotated
from sqlalchemy.orm import Session
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
async def get_user(user: user_dependency, db:db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Users).filter(Users.id == user.get("id")).first()


@router.get("/shopping-cart", status_code=status.HTTP_200_OK)
async def get_shopping_cart(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    #shopping_cart_model = db.query(ShoppingCart).filter(ShoppingCart.user_id == user.get("id")).all()
    shopping_cart_model = db.query(ShoppingCart, Foods).join(Foods, ShoppingCart.food_id == Foods.id)\
    .filter(ShoppingCart.user_id == user.get("id")).all()

    shopping_cart = []
    for shop, food in shopping_cart_model:
        shopping_cart.append({
            "id": shop.id,
            "food_id": shop.food_id,
            "food_name": food.food_name,
            "quantity": shop.quantity,
            "total_price": f"$ {shop.total_price}"
        })
    return shopping_cart


@router.post("/Add-to-cart/{food_id}", status_code=status.HTTP_201_CREATED)
async def add_to_cart(user: user_dependency,
                      db: db_dependency,
                      quantity: int = Query(gt=0),
                      food_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    food_model = db.query(Foods).filter(Foods.id == food_id).first()
    if not food_model:
        raise HTTPException(status_code=404, detail='Food not found')
    
    existing_shopping_cart = db.query(ShoppingCart, Foods.restaurant_id)\
        .join(Foods, ShoppingCart.food_id == Foods.id)\
        .filter(ShoppingCart.user_id == user.get('id'))\
        .all()
    
    if existing_shopping_cart:     
        for food in existing_shopping_cart:
            if food.restaurant_id != food_model.restaurant_id:
                raise HTTPException(status_code=400, detail='Cannot add food from different restaurants to the cart')

    total_price = food_model.price * quantity

    shopping_cart_item = ShoppingCart(
        quantity = quantity,
        food_id = food_id,
        total_price = total_price,
        user_id = user.get("id")
    )

    db.add(shopping_cart_item)
    db.commit()

    return shopping_cart_item


@router.put("/Add-to-cart/{food_id}", status_code=status.HTTP_201_CREATED)
async def update_shopping_cart(user: user_dependency,
                      db: db_dependency,
                      quantity: int = Query(gt=0),
                      food_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    my_shop_model = db.query(ShoppingCart).filter(ShoppingCart.food_id == food_id)\
    .filter(ShoppingCart.user_id == user.get('id')).first()

    if my_shop_model:
        food_model = db.query(Foods).filter(Foods.id == food_id).first()
        if not food_model:
            raise HTTPException(status_code=404, detail='Food not found')
        
        my_shop_model.quantity = quantity
        my_shop_model.total_price = food_model.price * quantity
    
    else:
        raise HTTPException(status_code=404, detail='Shopping cart item not found')

    db.commit()


@router.post("/purchase-shopping-cart", status_code=status.HTTP_204_NO_CONTENT)
async def purchase_shopping_cart(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    shopping_cart_model = db.query(ShoppingCart).filter(ShoppingCart.user_id == user.get('id')).all()

    if not shopping_cart_model:
        raise HTTPException(status_code=404, detail='The Shopping cart is empty')
    
    for item in shopping_cart_model:
        puchase_record = PurchaseRecords(
            quantity=item.quantity,
            food_id=item.food_id,
            total_price=item.total_price,
            user_id=item.user_id,
            purchase_date=item.purchase_date
        )
        db.add(puchase_record)

    db.query(ShoppingCart).filter(ShoppingCart.user_id == user.get('id')).delete()
    db.commit()


@router.delete("/Add-to-cart/{shopping_cart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food_in_shopping_cart(user: user_dependency, db: db_dependency, shopping_cart_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    shopping_cart_model = db.query(ShoppingCart).filter(ShoppingCart.id == shopping_cart_id)\
    .filter(ShoppingCart.user_id == user.get("id")).first()

    if shopping_cart_model is None:
        raise HTTPException(status_code=404, detail='Order not found')
    
    db.query(ShoppingCart).filter(ShoppingCart.id == shopping_cart_id)\
    .filter(ShoppingCart.user_id == user.get("id")).delete()

    db.commit()


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if not validate_passwd(user_verification.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must have at least one uppercase, one lowercase, one digit, one symbol, and be at least 6 characters long."
        )
    
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()

    if not bcrypt_context.verify(user_verification.password, user_model.hashed_password):
        raise HTTPException(status_code=401, detail='Error on password change')
    
    user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.add(user_model)
    db.commit()


@router.put("/email", status_code=status.HTTP_204_NO_CONTENT)
async def change_email(user: user_dependency, db: db_dependency, email_verification: EmailVerification):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if not validate_email(email_verification.new_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The Email is not valid')
    
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    user_model.email = email_verification.new_email
    db.add(user_model)
    db.commit()


@router.put("/phonenumber", status_code=status.HTTP_204_NO_CONTENT)
async def change_phonenumber(user: user_dependency, db: db_dependency, phonenumber_verification: PhoneNumberVerification):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    
    if not validate_phonenumber(phonenumber_verification.new_phonenumber):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The Email is not valid')
    
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    user_model.phonenumber = phonenumber_verification.new_phonenumber
    db.add(user_model)
    db.commit()