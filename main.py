from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from app.websocket_manager import manager

from app.routes.matches import router as matches_router
from app.routes.players import router as players_router
from app.routes.analytics import router as analytics_router
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rocket League MVP Tracker")

app.include_router(matches_router)
app.include_router(players_router)
app.include_router(analytics_router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintenir la connexion ouverte
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Optionnel : si tu ajoutes un dossier static plus tard
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass