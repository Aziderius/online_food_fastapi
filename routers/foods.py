from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models import Categories, Restaurants, Foods
from database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func, select
from sqlalchemy import join
from starlette import status


router = APIRouter(
    prefix='/foods',
    tags=['foods']
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_foods(db: db_dependency):
    return db.query(Foods).all()


@router.get("/food_name", status_code=status.HTTP_200_OK)
async def get_food_by_name(db: db_dependency, food_name: str = Query(...)):

    food_model = db.query(Foods).filter(func.lower(Foods.food_name).ilike(func.lower(f"%{food_name}%"))).all()
    if food_model is not None:
        return food_model
    
    raise HTTPException(status_code=404, detail="Food not found")


@router.get("/restaurants", status_code=status.HTTP_200_OK)
async def get_all_restaurants(db: db_dependency):
    restaurant_model = db.query(Restaurants).all()

    restaurant_info = []
    for restaurant in restaurant_model:
        restaurant_info.append({
            "id": restaurant.id,
            "restaurant_name": restaurant.restaurant_name,
            "category_id": restaurant.category_id,
            "address": restaurant.address,
            "rating": restaurant.rating
        })
    return restaurant_info


@router.get("/categories", status_code=status.HTTP_200_OK)
async def get_all_categories(db: db_dependency):
    return db.query(Categories).all()


@router.get("/restaurant", status_code=status.HTTP_200_OK)
async def get_restaurant_by_name(db: db_dependency, restaurant_name: str = Query(...)):

    restaurant_exact = db.query(Restaurants).filter(Restaurants.restaurant_name == restaurant_name).first()
    if restaurant_exact:
        return restaurant_exact
    
    restaurant_model = db.query(Restaurants).filter(func.lower(Restaurants.restaurant_name).ilike(func.lower(f"%{restaurant_name}%"))).all()
    if restaurant_model:
        return restaurant_model
    
    raise HTTPException(status_code=404, detail='Restaurant not found')


@router.get("/restaurant/{restaurant_id}", status_code=status.HTTP_200_OK)
async def get_food_by_restaurant_id(db: db_dependency, restaurant_id: int = Path(gt=0)):
    restaurant_model = db.query(Restaurants).filter(Restaurants.id == restaurant_id).first()

    foods_models = db.query(Foods).filter(Foods.restaurant_id == restaurant_id).all()

    if restaurant_model is not None:
        restaurant = {"restaurant_name" : restaurant_model.restaurant_name,
                      "category_id" : restaurant_model.category_id,
                      "address" : restaurant_model.address,
                      "rating" : restaurant_model.rating
        }

        return restaurant, foods_models
    
    raise HTTPException(status_code=404, detail="Restaurant not found")


@router.get("/categories/{category_id}", status_code=status.HTTP_200_OK)
async def get_restaurants_by_category(db: db_dependency, category_id: int = Path(gt=0)):

    category_model = db.query(Categories).filter(Categories.id == category_id).all()

    if category_model is not None:
        return category_model

    raise HTTPException(status_code=404, detail="category not found")        
    
    

    
