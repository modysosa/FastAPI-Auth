from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    id: str
    name: str

@app.post("/create/")
async def create_item(item: Item):
    return item

@app.get("/test/{item_id}/")
async def root(item_id: str, query: str = None):
    return {"message": item_id, "query": query}

