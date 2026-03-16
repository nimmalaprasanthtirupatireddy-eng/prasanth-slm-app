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
        # Root vector store directory
        self.root_db_path = os.path.join(os.getcwd(), "faiss_db")
        os.makedirs(os.path.join(os.getcwd(), "models", "embeddings"), exist_ok=True)
        os.makedirs(self.root_db_path, exist_ok=True)

    def _get_conv_path(self, conversation_id: str) -> str:
        return os.path.join(self.root_db_path, conversation_id)

    def add_document(self, text: str, conversation_id: str):
        """Chunk text and add to the FAISS vector store for a specific conversation."""
        if not conversation_id:
            return
            
        conv_path = self._get_conv_path(conversation_id)
        os.makedirs(conv_path, exist_ok=True)
        
        # Create chunks
        chunks = self.text_splitter.split_text(text)
        
        # Load existing index if it exists
        if os.path.exists(os.path.join(conv_path, "index.faiss")):
            vector_store = FAISS.load_local(
                conv_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            vector_store.add_texts(chunks)
        else:
            vector_store = FAISS.from_texts(chunks, self.embeddings)
        
        # Save local index
        vector_store.save_local(conv_path)

    def get_context(self, query: str, conversation_id: str, k: int = 7) -> str:
        """Search the vector store for relevant chunks if it exists for this conversation."""
        if not conversation_id:
            return ""
            
        conv_path = self._get_conv_path(conversation_id)
        
        # SPEED OPTIMIZATION: If no index exists, return early without any embedding or search
        if not os.path.exists(os.path.join(conv_path, "index.faiss")):
            return ""
        
        try:
            # Load index for this specific conversation
            vector_store = FAISS.load_local(
                conv_path, 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            
            # Perform similarity search
            docs = vector_store.similarity_search(query, k=k)
            
            # Combine snippets into context
            context = "\n\n---\n\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            print(f"RAG Error: {e}")
            return ""

    def clear(self, conversation_id: str):
        """Reset the vector store for a specific conversation."""
        if not conversation_id:
            return
            
        conv_path = self._get_conv_path(conversation_id)
        import shutil
        if os.path.exists(conv_path):
            shutil.rmtree(conv_path)

# Singleton instance
rag_handler = None

def get_rag_handler():
    global rag_handler
    if rag_handler is None:
        rag_handler = RAGHandler()
    return rag_handler
