from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7

class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    conversation_id: str

# Auth Schemas
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# History Schemas
class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
    class Config:
        from_attributes = True
