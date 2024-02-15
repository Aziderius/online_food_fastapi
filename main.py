from fastapi import FastAPI
import models
from database import engine
from routers import foods, auth, users


app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(foods.router)
app.include_router(users.router)
