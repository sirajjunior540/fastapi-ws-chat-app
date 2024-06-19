from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from sqlalchemy.orm import Session
from models import Base, engine, SessionLocal, User, Message
from pydantic import BaseModel

app = FastAPI()

templates = Jinja2Templates(directory="templates")
origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://192.168.1.103:8080/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UserCreate(BaseModel):
    name: str


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/register/")
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if ": " in data:
                sender, content = data.split(": ", 1)
                message = Message(content=content, sender=sender)
                db.add(message)
                db.commit()
                await manager.broadcast(data)
            else:
                # Handle improperly formatted messages if necessary
                print("Received improperly formatted message:", data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A user has left the chat")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
