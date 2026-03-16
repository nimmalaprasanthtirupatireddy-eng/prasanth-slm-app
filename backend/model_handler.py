import os
from llama_cpp import Llama
from typing import List
from .schemas import ChatMessage

class ModelHandler:
    def __init__(self):
        # Support for Llama 3.2 1B Instruct
        model_path = os.path.join(os.getcwd(), "models", "llama-3.2-1b-instruct-q4_k_m.gguf")
        
        # Fallback to Qwen if Llama not found (prevents crash during transition)
        if not os.path.exists(model_path):
            model_path = os.path.join(os.getcwd(), "models", "qwen2.5-0.5b-q6_k.gguf")
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No model found. Please download Llama 3.2 1B into {model_path}")
        
        print(f"Loading Brain: {os.path.basename(model_path)}")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096, # Increased context for Llama 3.2 RAG
            n_threads=os.cpu_count() or 4,
            verbose=False
        )

    def generate_response(self, messages: List[ChatMessage], max_tokens: int = 512, temperature: float = 0.7):
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        response = self.llm.create_chat_completion(
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response['choices'][0]['message']['content']

    def generate_stream(self, messages: List[ChatMessage], max_tokens: int = 512, temperature: float = 0.7):
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        stream = self.llm.create_chat_completion(
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        for chunk in stream:
            delta = chunk['choices'][0]['delta']
            if 'content' in delta:
                yield delta['content']

# Singleton instance
model_handler = None

def get_model_handler():
    global model_handler
    if model_handler is None:
        model_handler = ModelHandler()
    return model_handler
