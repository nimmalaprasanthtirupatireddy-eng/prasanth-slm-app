import os
from llama_cpp import Llama
from typing import List
from .schemas import ChatMessage

class ModelHandler:
    def __init__(self):
        model_path = os.path.join(os.getcwd(), "models", "qwen2.5-0.5b-q6_k.gguf")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=os.cpu_count() or 4,
            verbose=False
        )

    def generate_response(self, messages: List[ChatMessage], max_tokens: int = 512, temperature: float = 0.7):
        # Convert Pydantic messages to list of dicts for llama-cpp
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        response = self.llm.create_chat_completion(
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response['choices'][0]['message']['content']

# Singleton instance
model_handler = None

def get_model_handler():
    global model_handler
    if model_handler is None:
        model_handler = ModelHandler()
    return model_handler
