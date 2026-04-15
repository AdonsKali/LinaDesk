from .rag_manager import RAGManager
rag_manager = RAGManager()

def memory_save(query, content):
    text = f"{query}: {content}"
    rag_manager.add_document(text, metadata={"type": "conversation", "query": query})

def memory_search(query, top_k=5):
    results = rag_manager.search(query, top_k=top_k)
    return [result['text'] for result in results]

def add_document(text, metadata=None):
    rag_manager.add_document(text, metadata)

def add_documents(texts, metadatas=None):
    rag_manager.add_documents(texts, metadatas)

def clear_memory():
    rag_manager.clear()

# This file is not used anywhere in the project and can be removed.
# All RAG functionality is properly encapsulated in RAGService and RAGManager classes.
