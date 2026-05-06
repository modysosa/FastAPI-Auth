import sqlite3 
from pathlib import Path
from typing import Literal
from fastapi import Depends, FastAPI, Query
from fastapi import HTTPException, status, Response
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from jose import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm







app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "db_name.db"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def connect_to_db(db_name):
    conn = sqlite3.connect(str(db_name), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn
# create a table
def create_table(conn):
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)''')
    conn.commit()


def init_db():
    conn = connect_to_db(DB_NAME)
    try:
        create_table(conn)
    finally:
        conn.close()
# insert a user into the table
def insert_user(conn, name, email, password):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO users (name, email, password) VALUES (?, ?, ?)''', (name, email, password))
    conn.commit()
# get all users from the table
def get_all_users(conn):
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM users''')
    return cursor.fetchall()

# get user by id
def get_user_by_id(conn, user_id):
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM users WHERE id = ?''', (user_id,))
    return cursor.fetchone()


SECRET_KEY="your_secret_key"
ALGORITHM="HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")  #after that add get indpoint @get /me and @post tolen  to active authentication and return user info

class TokenData(BaseModel):
    username: str | None = None

# # example usage
# if __name__ == "__main__":
#     conn = connect_to_db('example.db')
#     create_table(conn)
#     insert_user(conn, 'Alice', 30)
#     insert_user(conn, 'Bob', 25)
#     users = get_all_users(conn)
#     for user in users:
#         print(user)
class User(BaseModel):
    id: int
    name: str
    email: str

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr

class UserCreate(BaseModel):
    name: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    name: str = Field(..., min_length=3)
    email: EmailStr


init_db()


@app.get("/users/")
def read_users(order: Literal["asc", "desc"] = Query("asc")):
    conn = connect_to_db(DB_NAME)
    try:
        cursor = conn.cursor()
        if order == "desc":
            cursor.execute("SELECT id, name, email FROM users ORDER BY id DESC")
        else:
            cursor.execute("SELECT id, name, email FROM users ORDER BY id ASC")
        users = [UserOut(id=row[0], name=row[1], email=row[2]) for row in cursor.fetchall()]
        return {"users": users}
    finally:
        conn.close()

@app.post("/login/")
def login_user(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    conn = connect_to_db(DB_NAME)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, password
            FROM users
            WHERE email = ?
        """, (form_data.username.lower(),))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        password_ok = bcrypt.checkpw(
            form_data.password.encode("utf-8"),
            user[3].encode("utf-8")
        )

        if not password_ok:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

        token_data = {
            "sub": str(user[0]),
            "email": user[2],
            "exp": expire
        }

        token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

        response.set_cookie(
            key="access_token",
            value=f"Bearer {token}",
            httponly=True,
            secure=False,      # True in production HTTPS
            samesite="lax",
            max_age=60 * 30,
            path="/"
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user[0],
                "name": user[1],
                "email": user[2]
            }
        }

    finally:
        conn.close()

@app.post("/users/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    conn = connect_to_db(DB_NAME)
    try:
        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")
        insert_user(conn, user.name, user.email, hashed_password)
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already exists")
    finally:
        conn.close()

@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    conn = connect_to_db(DB_NAME)
    try:
        existing_user = get_user_by_id(conn, user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET name = ?, email = ? WHERE id = ?''', (user.name, user.email, user_id))
        conn.commit()
        return {"message": "User updated successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already exists")
    finally:
        conn.close()


@app.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    return {"token": token}

@app.post("/logout/")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/"
    )
    return {"message": "Logged out"}


