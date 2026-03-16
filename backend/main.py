import uuid
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os

from . import schemas, model_handler, database, models, auth

# Initialize Database
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Qwen2.5 Mobile Chat API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Endpoints ---

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# --- Chat & History Endpoints ---

@app.get("/api/conversations", response_model=List[schemas.ConversationResponse])
def get_conversations(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id
    ).order_by(models.Conversation.created_at.desc()).all()

@app.get("/api/conversations/{conversation_id}/messages", response_model=List[schemas.MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    conversation = db.query(models.Conversation).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.messages

@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        conv_id = request.conversation_id
        
        # Create new conversation if ID not provided
        if not conv_id:
            conv_id = str(uuid.uuid4())
            # Auto-generate title from first message
            title = (request.messages[0].content[:30] + "...") if request.messages else "New Chat"
            new_conv = models.Conversation(id=conv_id, title=title, user_id=current_user.id)
            db.add(new_conv)
            db.commit()

        # Save user message
        last_msg = request.messages[-1]
        user_msg = models.Message(conversation_id=conv_id, role="user", content=last_msg.content)
        db.add(user_msg)

        # Generate LLM response
        handler = model_handler.get_model_handler()
        content = handler.generate_response(
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Save assistant message
        assistant_msg = models.Message(conversation_id=conv_id, role="assistant", content=content)
        db.add(assistant_msg)
        db.commit()

        return schemas.ChatResponse(
            id=str(uuid.uuid4()),
            role="assistant",
            content=content,
            conversation_id=conv_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {"status": "ok"}

# Serve static files
static_dir = os.path.join(os.getcwd(), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
