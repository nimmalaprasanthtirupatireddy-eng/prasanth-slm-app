import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List

class RAGHandler:
    def __init__(self):
        # Initialize embeddings model (Sentence-Transformers)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            cache_folder=os.path.join(os.getcwd(), "models", "embeddings")
        )
        # Initialize text splitter - smaller chunks for better granularity on dense docs like resumes
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=150,
            add_start_index=True
        )
        # Vector store storage path
        self.db_path = os.path.join(os.getcwd(), "faiss_db")
        self.vector_store = None
        
        # Ensure models and db directories exist
        os.makedirs(os.path.join(os.getcwd(), "models", "embeddings"), exist_ok=True)
        os.makedirs(self.db_path, exist_ok=True)

    def add_document(self, text: str):
        """Chunk text and add to the FAISS vector store."""
        # Create chunks
        chunks = self.text_splitter.split_text(text)
        
        if self.vector_store is None:
            # Create first vector store
            self.vector_store = FAISS.from_texts(chunks, self.embeddings)
        else:
            # Add to existing store
            self.vector_store.add_texts(chunks)
        
        # Save local index
        self.vector_store.save_local(self.db_path)

    def get_context(self, query: str, k: int = 7) -> str:
        """Search the vector store for relevant chunks."""
        if self.vector_store is None:
            # Try loading existing index if present
            if os.path.exists(os.path.join(self.db_path, "index.faiss")):
                self.vector_store = FAISS.load_local(
                    self.db_path, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
            else:
                return ""
        
        # Perform similarity search
        docs = self.vector_store.similarity_search(query, k=k)
        
        # Combine snippets into context
        context = "\n\n---\n\n".join([doc.page_content for doc in docs])
        return context

    def clear(self):
        """Reset the vector store."""
        import shutil
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)
            os.makedirs(self.db_path)
        self.vector_store = None

# Singleton instance
rag_handler = None

def get_rag_handler():
    global rag_handler
    if rag_handler is None:
        rag_handler = RAGHandler()
    return rag_handler
