from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from .auth import get_current_user
from pydantic import BaseModel, Field
from models import ShoppingCart, Foods, Users, PurchaseRecords
from starlette import status
from passlib.context import CryptContext


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
