
# Request Body
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()
@app.get("/")
def root():
    return {"message": "Hello World"}


items = [
    {"id":1 , "name":"book" , "price": 10, "stock": True},
    {"id":2 , "name":"pen" , "price": 20, "stock": False},
    {"id":3 , "name":"book" , "price": 30, "stock": True},
    {"id":4 , "name":"pencil" , "price": 40, "stock": False},
    {"id":5 , "name":"eraser" , "price": 50, "stock": True},
    {"id":6 , "name":"ruler" , "price": 60, "stock": False},
    {"id":7 , "name":"marker" , "price": 70, "stock": True},
    {"id":8 , "name":"highlighter" , "price": 80, "stock": False},
    {"id":9 , "name":"stapler" , "price": 90, "stock": True},
    {"id":10 , "name":"paper clips" , "price": 100, "stock": False},
]

@app.get("/items")
async def get_items(start: int = 0,
                     limit: int = 20,
                     id: int = None,
                     name: str = None):
    if id :
        for item in items:
            if item["id"] == id:
                return [item]
        return {"message": "Item not found"}
    if name:
        filterdList = []
        for item in items:
            if item["name"] == name:
                filterdList.append(item)
        if filterdList:
            return filterdList
        return {"message": "Item not found"}
    return items[start : start + limit]


# http://127.0.0.1:8000/items/prices?range=50
@app.get("/items/prices")
async def sort_items_by_price(range: int = None):
    sorted_items = sorted(items, key=lambda x: x["price"], reverse=True)
    if range :
        sorted_items = [ item for item in sorted_items if item["price"] <= range ]
        return sorted_items
    else:
        return sorted_items


@app.get("/items/stock")
async def filter_items_by_stock(in_stock: bool = True):
    if not in_stock :
        item = [ item for item in items if item["stock"] == False ]
        return item
    else:
        item = [ item for item in items if item["stock"] == True ]
        return item

# from typing import Optional

# @app.get("/items/stock")
# async def filter_items_by_stock(instock: Optional[bool] = None):
#     if instock is None:
#         return items
#     return [item for item in items if item["stock"] == instock]


# Lesson 4 : Request Body

class Item(BaseModel):
    id: int
    name: str
    description: str | None = None
    price: float
    tax: float | None = None
    stock: bool

@app.post("/items")
async def create_item(item: Item):
    # dectionary = item.model_dump()
    # dect is using to convert the pydantic model to a dictionary 
    # but in fastapi we can directly use the pydantic (model_dump) model 
    # as a request body and it will automatically convert it to a dictionary for us.
    # add item dictionary to the items list
    # items.append(item.model_dump())
    item_dict = item.model_dump()
    price_with_tax = item.price + item.tax if item.tax else item.price
    item_dict["price_with_tax"] = price_with_tax
    items.append(item_dict)
    return item_dict

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    # return {"item_id": item_id, **item.model_dump()}
    for i, existing_item in enumerate(items):
        if existing_item["id"] == item_id:
            items[i] = item.model_dump()
            return items[i]
    return {"message": "Item not found"}
