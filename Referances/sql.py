import sqlite3 
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field
import bcrypt




app = FastAPI()
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "db_name.db"

def connect_to_db(db_name):
    conn = sqlite3.connect(str(db_name))
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
    password: str

class UserCreate(BaseModel):
    name: str = Field(..., min_length=3)
    email: EmailStr
    password: str = Field(..., min_length=8)    


@app.get("/users/")
def read_users(order: str = Query("asc")):
    conn = connect_to_db(DB_NAME)
    try:
        create_table(conn)
        cursor = conn.cursor()
        if order == "desc":
            cursor.execute("SELECT * FROM users ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM users ORDER BY id ASC")
        users = cursor.fetchall()
        return {"users": users}
    finally:
        conn.close()


@app.post("/users/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate):
    conn = connect_to_db(DB_NAME)
    try:
        create_table(conn)
        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        insert_user(conn, user.name, user.email, hashed_password)
        return {"message": "User created successfully"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User id already exists")
    finally:
        conn.close()

@app.put("/users/{user_id}")
def update_user(user_id: int, user: User):
    conn = connect_to_db(DB_NAME)
    try:
        create_table(conn)
        existing_user = get_user_by_id(conn, user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="User not found")
        cursor = conn.cursor()
        cursor.execute('''UPDATE users SET name = ?, email = ? WHERE id = ?''', (user.name, user.email, user_id))
        conn.commit()
        return {"message": "User updated successfully"}
    finally:
        conn.close()

