# backend/src/backend/main.py
import uvicorn
import socketio
from fastapi import FastAPI, Response

app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)


@app.get("/")
async def root():
    return {"status": "online", "service": "chess-multiplayer-backend"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")


def main():
    uvicorn.run(asgi_app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
