import os
import uvicorn

from modules_scan.core_links import init_db
from modules_app.app_setup import create_app
from modules_app.routes import router as routes_router

app = create_app()
app.include_router(routes_router)

@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT")), reload=False)