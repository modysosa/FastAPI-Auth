from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}


item = [
    {"name": "Item 1", "price": 10.0, "is_offer": False},
    {"name": "Item 2", "price": 20.0, "is_offer": True},
    {"name": "Item 3", "price": 30.0, "is_offer": False},
    {"name": "Item 4", "price": 40.0, "is_offer": True},
    {"name": "Item 5", "price": 50.0, "is_offer": False},
]


@app.get("/items/")
def read_items():
    return item
