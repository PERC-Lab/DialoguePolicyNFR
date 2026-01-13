import uuid
from datetime import datetime
from typing import Dict, List, Optional

class Chatbot:
    def __init__(self):
        print("Chatbot initialized")
        self.uuid = str(uuid.uuid4())
        self.chat_history: List[Dict] = []
    
    def get_uuid(self) -> str:
        """Return the unique identifier for this chatbot instance."""
        return self.uuid
    
    def create_chat(self) -> str:
        """Initialize a new chat session and return the UUID."""
        self.chat_history = []
        return self.uuid
    
    def ask_chatbot(self, request: str) -> Dict:
        """
        Process a user request and return a mock response.
        
        Args:
            request: The user's message/question
            
        Returns:
            Dictionary containing the bot's response with timestamp
        """
        user_time = datetime.now().isoformat()
        
        
        # Simple mock: cycle through responses or provide a generic one
        import random
        bot_reply = f"You said: {request}"
        
        bot_time = datetime.now().isoformat()
        
        # Add to chat history
        chat_entry = {
            'user_message': request,
            'bot_reply': bot_reply,
            'user_time': user_time,
            'bot_time': bot_time
        }
        self.chat_history.append(chat_entry)
        
        return {
            'response': bot_reply,
            'timestamp': bot_time
        }
    
    def get_chat_history(self) -> List[Dict]:
        """Return the full chat history."""
        return self.chat_history
