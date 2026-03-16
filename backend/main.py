import uuid
import os
import io
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pymupdf4llm

from . import schemas, model_handler, database, models, auth, rag_handler

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

@app.patch("/api/conversations/{conversation_id}", response_model=schemas.ConversationResponse)
def update_conversation(
    conversation_id: str,
    update: schemas.ConversationUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    conversation = db.query(models.Conversation).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.user_id == current_user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.title = update.title
    db.commit()
    db.refresh(conversation)
    return conversation

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(
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
    
    # Delete associated messages first (manual due to SQLite constraints sometimes)
    db.query(models.Message).filter(models.Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()
    return {"status": "deleted"}

@app.post("/api/upload", response_model=schemas.FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user)
):
    content = ""
    filename = file.filename
    temp_path = f"temp_{filename}"
    
    try:
        if filename.endswith(".pdf"):
            # PyMuPDF4LLM works best with a file path
            with open(temp_path, "wb") as f:
                f.write(await file.read())
            
            content = pymupdf4llm.to_markdown(temp_path)
        else:
            # Default to text
            file_bytes = await file.read()
            content = file_bytes.decode("utf-8", errors="ignore")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Index for RAG
    if content:
        rag = rag_handler.get_rag_handler()
        rag.add_document(content)
    
    return {"content": content, "filename": filename}

@app.delete("/api/rag")
async def clear_rag(
    current_user: models.User = Depends(auth.get_current_user)
):
    rag = rag_handler.get_rag_handler()
    rag.clear()
    return {"message": "RAG index cleared"}

@app.post("/api/chat")
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
            title = (request.messages[0].content[:30] + "...") if request.messages else "New Chat"
            new_conv = models.Conversation(id=conv_id, title=title, user_id=current_user.id)
            db.add(new_conv)
            db.commit()

        # Save user message
        last_msg = request.messages[-1]
        user_msg = models.Message(conversation_id=conv_id, role="user", content=last_msg.content)
        db.add(user_msg)
        db.commit()

        async def stream_generator():
            handler = model_handler.get_model_handler()
            rag = rag_handler.get_rag_handler()
            
            # Retrieval Step
            context = rag.get_context(last_msg.content)
            
            # Augment prompt if context exists
            augmented_messages = list(request.messages)
            if context:
                rag_prompt = f"Use the following context to answer the user's question. If you don't know the answer, just say you don't know based on the context.\n\nContext:\n{context}\n\nQuestion: {last_msg.content}"
                # Replace the last user message content with the augmented one for the LLM
                augmented_messages[-1] = schemas.ChatMessage(role="user", content=rag_prompt)

            full_content = ""
            
            # Send initial metadata
            yield f"event: metadata\ndata: {{\"conversation_id\": \"{conv_id}\"}}\n\n"
            
            for chunk in handler.generate_stream(
                messages=augmented_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            ):
                full_content += chunk
                yield f"data: {chunk}\n\n"
            
            # Save assistant message at the end
            # We need a new session here because this is an async generator
            new_db = database.SessionLocal()
            try:
                assistant_msg = models.Message(conversation_id=conv_id, role="assistant", content=full_content)
                new_db.add(assistant_msg)
                new_db.commit()
            finally:
                new_db.close()
            
            yield "event: end\ndata: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

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
