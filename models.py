from database import Base
from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy import DateTime, func


class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True)
    phonenumber = Column(String, unique=True)
    hashed_password = Column(String)
    role = Column(String)


class Categories(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, unique=True)


class Restaurants(Base):
    __tablename__ = 'restaurants'

    id = Column(Integer, primary_key=True, index=True)
    restaurant_name = Column(String, unique=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    address = Column(String, unique=True)
    rating = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"))


class Foods(Base):
    __tablename__ = 'foods'

    id = Column(Integer, primary_key=True, index=True)
    food_name = Column(String)
    price = Column(Float)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    description = Column(String)


class ShoppingCart(Base):
    __tablename__ = 'shopping_cart'

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer)
    food_id = Column(Integer, ForeignKey("foods.id"))
    total_price = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    purchase_date = Column(DateTime, server_default=func.now())


class PurchaseRecords(Base):
    __tablename__ = 'purchase_records'

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer)
    food_id = Column(Integer, ForeignKey("foods.id"))
    total_price = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"))
    purchase_date = Column(DateTime, server_default=func.now())
