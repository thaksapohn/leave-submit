import flet.fastapi
from app_ui import build_app  # <- หน้าที่สร้าง Flet UI

app = flet.fastapi.app(build_app)