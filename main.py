# import flet.fastapi
# from app_ui import main  # <- หน้าที่สร้าง Flet UI

# app = flet.fastapi.app(main)


from flet.fastapi import app as flet_app
from app_ui import main

flet_app(main)
