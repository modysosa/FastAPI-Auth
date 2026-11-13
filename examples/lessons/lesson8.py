# Multiple Parameters

from typing import Optional

from fastapi import FastAPI, Path, Query, Body
from pydantic import BaseModel, Field
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

# @app.post("/items/")
# async def create_item(
#     name: str = Query(..., min_length=3, max_length=50, description="The name of the item"),
#     price: float = Query(..., gt=0, le=1000, description="The price of the item"),
#     description: str = Query(None, max_length=300, description="A brief description of the item")
# ):
#     return {"name": name, "price": price, "description": description}

class Item(BaseModel):
    name: str = Field(..., min_length=3, max_length=50, description="The name of the item")
    price: float = Field(..., gt=0, le=1000, description="The price of the item")
    description: Optional[str] = Field(None, max_length=300, description="A brief description of the item")

class User(BaseModel):
    username: str # by default required
    # full_name: Optional[str] = None # optional field with default value of None

class UserMail(User):
    email: str
    # email: str | None = Field(None, description="The email of the user")
    # email: Optional[str] = Field(None, description="The email of the user")
    # email: Optional[str] = Field(None, description="The email of the user", max_length=100)




@app.put("/items/{item_id}")
async def update_item(
    *,
    item_id: int = Path(..., gt=0, title="Item ID", description="The ID of the item"),
    q : str | None = Query(None, max_length=50, description="Query string for the item"),
    item: Item | None = None,
    user: UserMail | None = None,
    age: int = Body(..., gt=0, le=120, description="The age of the user")

):
    result = {"item_id": item_id}
    if q:
        result.update({"q": q})
    if item:
        result.update({"item": item.dict()})
    if user:
        result.update({"user": user.dict()})
    if age is not None:
        result.update({"age": age})


    
    return result

