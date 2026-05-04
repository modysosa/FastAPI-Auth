# Query Parameters
from fastapi import FastAPI
from enum import Enum



app = FastAPI()

@app.get("/users/")
async def listUsers():
    return {"message": "this is list of users"}

# static needs to be defined before dynamic
@app.get("/users/1", include_in_schema=False)
async def adminUser():
    return {"message": "this is admin user"}

# dynamic route
@app.get("/users/{user_id}")
async def getUser(user_id: int):
    return {"message": f"this is user with id:{user_id}"}

class UserList(str, Enum): 
    admin = 1
    manager = 2
    user = 3


@app.get("/{user_type}/{user_id}")
async def getUserType(user_type: UserList, user_id: int):
    return {"message": {"user_type": user_type.name, "user_id": user_id}}
