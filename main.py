from fastapi import FastAPI
from flet.fastapi import AppService
from app_ui import main

app = FastAPI()
flet_app = AppService(target=main)

app.mount("/", flet_app.app)