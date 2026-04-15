from typing import List, Dict, Any
from backend.infrastructure.services.RAG.rag_manager import RAGManager
from logger import log


class RAGService:
    """
    Service class to handle RAG functionality throughout the application
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = None):
        try:
            self.rag_manager = RAGManager(model_name=model_name, index_path=index_path)
            log("RAG Service initialized successfully", 'info', __name__)
        except Exception as e:
            log(f"Error initializing RAG Service: {str(e)}", 'error', __name__)
            # Fallback to default initialization
            self.rag_manager = RAGManager(model_name=model_name)
    
    def add_conversation(self, user_input: str, ai_response: str, session_id: str = None):
        """
        Add a conversation pair to the RAG memory
        """
        try:
            content = f"User: {user_input}\nAssistant: {ai_response}"
            metadata = {
                "type": "conversation",
                "user_input": user_input,
                "ai_response": ai_response
            }
            if session_id:
                metadata["session_id"] = session_id
                
            self.rag_manager.add_document(content, metadata)
            log(f"Added conversation to RAG: {user_input[:50]}...", 'debug', __name__)
        except Exception as e:
            log(f"Error adding conversation to RAG: {str(e)}", 'error', __name__)
    
    def add_document(self, content: str, doc_type: str = "general", metadata: Dict[str, Any] = None):
        """
        Add a general document to the RAG memory
        """
        try:
            if metadata is None:
                metadata = {}
            
            metadata.update({"type": doc_type})
            self.rag_manager.add_document(content, metadata)
            log(f"Added document to RAG: {content[:50]}...", 'debug', __name__)
        except Exception as e:
            log(f"Error adding document to RAG: {str(e)}", 'error', __name__)
    
    def search_relevant_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant context based on the query
        """
        try:
            results = self.rag_manager.search(query, top_k)
            log(f"RAG search for '{query[:30]}...' found {len(results)} results", 'debug', __name__)
            return results
        except Exception as e:
            log(f"Error searching RAG: {str(e)}", 'error', __name__)
            return []
    
    def get_context_for_query(self, query: str, top_k: int = 3) -> str:
        """
        Get formatted context for a query to be used in prompting
        """
        try:
            results = self.search_relevant_context(query, top_k)
            
            if not results:
                log(f"No relevant context found for query: {query[:50]}...", 'debug', __name__)
                return ""
            
            context_parts = ["Relevant context from previous conversations:"]
            for i, result in enumerate(results, 1):
                # Extract just the content part without the metadata
                text = result['text']
                if 'User:' in text and 'Assistant:' in text:
                    # Format as a conversation snippet
                    context_parts.append(f"Past conversation #{i}: {text}")
                else:
                    context_parts.append(f"Information #{i}: {text[:300]}...")
            
            context_str = "\n".join(context_parts)
            log(f"Generated RAG context: {context_str[:100]}...", 'debug', __name__)
            return context_str
        except Exception as e:
            log(f"Error generating RAG context: {str(e)}", 'error', __name__)
            return ""
    
    def clear_memory(self):
        """
        Clear all stored memory
        """
        try:
            self.rag_manager.clear()
            log("RAG memory cleared", 'info', __name__)
        except Exception as e:
            log(f"Error clearing RAG memory: {str(e)}", 'error', __name__)
    
    def delete_by_session(self, session_id: str):
        """
        Delete all entries associated with a specific session
        """
        try:
            self.rag_manager.delete_by_metadata("session_id", session_id)
            log(f"Deleted RAG entries for session {session_id}", 'info', __name__)
        except Exception as e:
            log(f"Error deleting RAG entries for session {str(e)}", 'error', __name__)