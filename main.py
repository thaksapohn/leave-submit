from fastapi import FastAPI
from flet.fastapi import FletApp
from app_ui import main  # ฟังก์ชันสร้าง UI ของคุณ

# Create FastAPI app
api = FastAPI()

# Create FletApp and mount it
flet_app = FletApp(target=main)
flet_app.mount(api)

# Export 'api' as app entrypoint
app = api