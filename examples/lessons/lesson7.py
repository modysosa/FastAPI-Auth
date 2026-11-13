
# Numeric Validation

# the defrance between path and query parameters is that path parameters are part of the URL path, while query parameters are included in the URL after a question mark (?). Path parameters are typically used to identify specific resources, while query parameters are used to filter or modify the response based on certain criteria.
# what that mean path mean https://example.com/items/5 and query mean https://example.com/items?price=10.5   ??? is query 

from fastapi import FastAPI, Query, Path
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_items(
    item_id: int = Path(..., gt=0 , title = "Item Id" , description = "item is must be a positive integer"),
      price: float = Query(..., gt=0, le=1000, description = "item is must be a positive integer")): # gt grater than le less or equal
    # gt = 0  # greater than 0
    # lt = 1000  # less than 1000
    return {"item_id": item_id, "price": price}

@app.get("/items/{item_price}")
async def read_items_by_price(
    min_price: float = Query(..., gt=0, le=1000, description = "item is must be a positive integer"),
    max_price: float = Query(..., ge=1, le=1000, description = "item is must be a positive integer")

):
    return {"min_price": min_price, "max_price": max_price}
