# Fields
# https://www.youtube.com/watch?v=-zMrbGZ4E_8&list=PLGbzY-VLUfcpzhB-iyGvju-NMMez_NNP9&index=9


from fastapi import FastAPI, Query, Path, Body
from pydantic import BaseModel, Field


app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

class Item(BaseModel):
    name: str 
    description: str | None = Field(None, max_length=300, description="A brief description of the item")
    price: float = Field(..., gt=0, le=1000, description="The price of the item")


@app.put("/items/{item_id}")
async def update_item(
    item_id: int = Path(..., gt=0),
    item: Item = Body(..., embedded=True)
):
    result = {"item_id": item_id, "item": item}
    return result
