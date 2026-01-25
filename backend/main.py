from fastapi import FastAPI

app = FastAPI()

#Start of a beginning
@app.get("/")
def root():
    return {"Hello": "World"}