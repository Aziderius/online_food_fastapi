from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from sqlalchemy.orm import Session
from database import SessionLocal
from pydantic import BaseModel
from models import Users
from starlette import status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime
import phonenumbers
from email_validator import validate_email

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRET_KEY = '87c8950a0b7db9dd5d3eac0d5e84460862121fe5f560f71857dd4b936927d22d'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

class CreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phonenumber:str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(phonenumber: str, password:str, db):
    user = db.query(Users).filter(Users.phonenumber == phonenumber).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def validate_passwd(password):
    u_case = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    l_case = 'abcdefghijklmnopqrstuvwxyz'
    num = '0123456789'
    sym = "|°!#$%&/()=?¡*¨[_:;]^~@\~^,.-{+}¿'/"

    if not any(character in u_case for character in password):
        return False
    
    if not any(character in l_case for character in password):
        return False
    
    if not any(character in num for character in password):
        return False
    
    if not any(character in sym for character in password):
        return False

    if len(password) < 6:
        return False
    
    return True


#Funcion para validar telefono usando libreria Phonenumber    
def validate_phonenumber(phone_number):
    phone_number = "+52" + phone_number  # Agregamos la lada directamente
 
    parsed_number = phonenumbers.parse(phone_number, None)

    if phonenumbers.is_valid_number(parsed_number):    
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)


#Funcion para validar nombre/nombres del usuario
def validate_name(first_name):
    names = first_name.split()

    if all(name.isalpha() for name in names):
        return names


#Funcion para validar que solo se coloque 1 apellido y que no contenga numeros ni simbolos
def validate_last_name(last_name):
    if last_name.isalpha():
        return last_name


def create_access_token(first_name: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': first_name, 'id':user_id, 'role': role}
    expires = datetime.utcnow() + expires_delta
    encode.update({'exp':expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        first_name: str = payload.get('sub')
        user_id: int = payload.get('id')
        user_role: str = payload.get('role')
        if first_name is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')
        
        return {'first_name': first_name, 'id': user_id, 'user_role': user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')
    

@router.post("/", status_code=status.HTTP_201_CREATED)
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
        hashed_password = bcrypt_context.hash(create_user_request.password)
    )
    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')
    
    token = create_access_token(user.phonenumber, user.id, user.role, timedelta(minutes=20))

    return {'access_token': token, 'token_type': 'bearer'}