# Nested Models

from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}



class Image(BaseModel):
    url: HttpUrl
    name: str

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None
    image: Image | None = None

class Product(BaseModel):
    item: Item
    image: Image  

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
    result = {"item_id": item_id, "item": item}
    if item.tax:
        total_price = item.price + item.tax
        result.update({"total_price": total_price})
    return result

@app.post("/products/{item_id}")
async def create_product(item: Item, image : Image):
    product = {"item": item, "image": image}
    return {"product": product}
