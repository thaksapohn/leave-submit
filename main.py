from fastapi import FastAPI
from flet.fastapi import AppService
from app_ui import build_app

app = FastAPI()
flet_app = AppService(target=build_app)

app.mount("/", flet_app.app)