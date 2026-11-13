# Query Parameters
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/", deprecated=True, description="This is a post request")
async def post():
    return {"message": "Post request received"}

@app.put("/", description="This is a put request")
async def put():
    return {"message": "Put request received"}
