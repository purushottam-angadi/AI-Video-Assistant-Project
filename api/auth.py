import os
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
import psycopg2
import psycopg2.extras

auth_router= APIRouter()

SECRET_KEY= os.getenv("JWT_SECRET_KEY", "default_secret_key")

ALGORITHM="HS256"

ACCESS_TOKEN_EXPIRE_MINUTES= 60*24*10

pwd_context= CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

DATABASE_URL = os.getenv("DATABASE_URL")


def get_db():
    con=psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return con

def init_db():
    con= get_db()
    cur=con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    con.commit()
    cur.close()
    con.close()



def hash_password(password:str)-> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password :str)->bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id :str)->str:
    expire= datetime.now(timezone.utc)+ timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload={"sub": user_id, "exp": expire}
    token= jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_current_user(token: str = Depends(oauth2_scheme)):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload=jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str= payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:    
        raise credentials_exception


class SignupRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@auth_router.post("/signup", status_code= 201)
def signup(req: SignupRequest):
    con=get_db()
    cur=con.cursor()
    try:
        hashed=hash_password(req.password)
    
        cur.execute(
            "INSERT INTO users (username, hashed_password) VALUES (%s, %s) RETURNING id",
            (req.username, hashed),
        )
        new_user_id= cur.fetchone()["id"]
        con.commit()
        return {"message": "User created successfully", "user_id": new_user_id}

    except psycopg2.errors.UniqueViolation:
        con.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")

    finally:
        cur.close()
        con.close()


@auth_router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm =Depends()):
    con=get_db()
    cur=con.cursor()
    try:
     cur.execute(
    "SELECT id, hashed_password FROM users WHERE username = %s",
    (form_data.username,),
    )
     row=cur.fetchone()
     if not row or not verify_password(form_data.password, row["hashed_password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")

     token=create_access_token(user_id=str(row["id"]))
     return {"access_token": token, "token_type": "bearer"}


    finally:
     cur.close()
     con.close()


@auth_router.get("/me")
def read_current_user(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}