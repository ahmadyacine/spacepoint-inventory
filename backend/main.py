from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import auth, users, instructors, cubesats, workshops, dashboard, receipts, notifications, websockets

app = FastAPI(title="SpacePoint Inventory API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(instructors.router)
app.include_router(cubesats.router)
app.include_router(workshops.router)
app.include_router(dashboard.router)
app.include_router(receipts.router)
app.include_router(notifications.router)
app.include_router(websockets.router)


from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/api-status")
def root():
    return {"message": "SpacePoint Inventory API (PostgreSQL version)"}
