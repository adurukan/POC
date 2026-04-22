from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/visuals", StaticFiles(directory="visuals"), name="visuals")
