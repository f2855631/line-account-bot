import asyncio
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.dependencies import get_db
from src.routers import liff, records, targets, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting, connecting to DB...")
    db = get_db()
    retries = 5
    while retries > 0:
        try:
            db.db.execute_query("SELECT 1", fetch=True)
            print("✅ DB Connected & Ready!")
            break
        except Exception as e:
            retries -= 1
            print(f"❌ DB connection failed. Retries left: {retries}. Error: {e}")
            if retries == 0:
                print("🚨 Could not connect to DB. Application might not work properly.")
            await asyncio.sleep(5)
    yield
    print("🛑 App shutting down...")


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(liff.router)
app.include_router(records.router)
app.include_router(targets.router)
app.include_router(webhook.router)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
