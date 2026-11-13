

# Query String Validation
#  anything after the ? in the URL is called query string
#  we can validate the query string using the Query class from fastapi
#  https://example.com/items?name=book&price=10


from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/")
async def read_items(name: str = Query(..., min_length=3, max_length=50, regex="^[a-zA-Z\s]+$"),
                      email: str = Query(..., max_length=50, regex="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")):   
    # regex = "^[a-zA-Z0-9]+$"  # only allow alphanumeric characters 
    # = "^fixedquery$"  # only allow the exact string "fixedquery" 
    # = "^[a-zA-Z\s]+$"  # only allow letters and spaces
    return {"name": name, "email": email}


