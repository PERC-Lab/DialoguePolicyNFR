import subprocess
import os
import shlex
from datetime import datetime
from typing import Dict, List, Optional

STATIC_PROJECT_PATH = "/Users/neo/Desktop/NFR/new/website-server-copy/iTrust/iTrust"

class Chatbot:
    def __init__(self, project_path: str = STATIC_PROJECT_PATH, uuid: Optional[str] = None):
        """
        Initialize the chatbot with copilot CLI integration.
        
        Args:
            project_path: Path to the project directory
            uuid: Optional existing UUID to resume a session
        """
        print(f"Initializing chatbot with project path: {project_path} and uuid: {uuid}")
        self.project_path = project_path
        self.uuid = uuid
        self.chat_history: List[Dict] = []
        
        # Load initial prompt if it exists
        initial_prompt = None
        prompt_file = os.path.join(os.path.dirname(__file__), 'instruction_prompt.txt')
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r') as file:
                initial_prompt = file.read()
        
        # If no UUID provided, create a new chat session
        # todo check uuid is valid
        if not self.uuid:
            self.uuid = self.create_chat(initial_prompt=initial_prompt)
    
    def create_chat(self, initial_prompt: Optional[str] = None, timeout: int = 180) -> str:
        """
        Create a new chat session with copilot CLI and return the UUID.
        
        Args:
            initial_prompt: Optional initial prompt/instructions to send when creating the session
            timeout: Maximum time to wait for session creation
            
        Returns:
            The session UUID from copilot
        """
        # Use a dummy prompt if none provided
        prompt = initial_prompt if initial_prompt else "."
        
        # Properly escape the prompt for shell command
        escaped_prompt = shlex.quote(prompt)
        escaped_path = shlex.quote(self.project_path)
        
        # Create a new session by running a command and extracting the session ID
        shell_command = (
            f'cd {escaped_path} && '
            f'copilot -p {escaped_prompt} --model gpt-5.1-codex-max -s --allow-all-tools 2>/dev/null >/dev/null && '
            f'ls -t ~/.copilot/logs/ 2>/dev/null | head -n 1 | sed "s/\\.log$//"'
        )
        
        try:
            result = subprocess.run(
                shell_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_path,
                env={**os.environ, 'PATH': f"{os.path.expanduser('~')}/.local/bin:{os.environ.get('PATH', '')}"},
                timeout=timeout
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # Extract UUID from the log filename
                    # Format could be: session-{uuid} or just {uuid}
                    if output.startswith('session-'):
                        uuid = output[8:]  # Remove 'session-' prefix
                    else:
                        uuid = output
                    self.chat_history = []
                    return uuid
                else:
                    raise Exception("Failed to retrieve session ID from copilot logs")
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(f"Failed to create chat: {error_msg}")
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout: copilot create-chat took longer than {timeout} seconds")
        except Exception as e:
            raise Exception(f"Error creating copilot chat: {str(e)}")
    
    def ask_cursor_agent(self, message: str, timeout: int = 600) -> str:
        """
        Ask a question to copilot CLI using the current session UUID.
        
        Args:
            message: The message/question to ask
            timeout: Maximum time to wait for response
            
        Returns:
            The response from copilot
        """
        if not self.uuid:
            raise Exception("UUID not initialized. Cannot ask copilot.")
        
        # Properly escape the message for shell command
        # Use shlex.quote to safely escape special characters
        escaped_message = shlex.quote(message)
        escaped_uuid = shlex.quote(self.uuid)
        escaped_path = shlex.quote(self.project_path)
        
        shell_command = (
            f'cd {escaped_path} && '
            f'copilot --model gpt-5.1-codex-max --resume {escaped_uuid} -p {escaped_message} -s --allow-all-tools'
        )
        
        try:
            result = subprocess.run(
                shell_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_path,
                env={**os.environ, 'PATH': f"{os.path.expanduser('~')}/.local/bin:{os.environ.get('PATH', '')}"},
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(f"Failed to ask copilot: {error_msg}")
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout: copilot took longer than {timeout} seconds to respond")
        except Exception as e:
            raise Exception(f"Error asking copilot: {str(e)}")
    
    def get_uuid(self) -> str:
        """Return the unique identifier for this chatbot instance."""
        return self.uuid
    
    def ask_chatbot(self, request: str) -> Dict:
        """
        Process a user request and return the response from copilot.
        
        Args:
            request: The user's message/question
            
        Returns:
            Dictionary containing the bot's response with timestamp
        """
        user_time = datetime.now().isoformat()
        
        try:
            # Ask copilot CLI
            bot_reply = self.ask_cursor_agent(request)
            bot_reply = bot_reply.strip()
        except Exception as e:
            bot_reply = f"Error: {str(e)}"
        
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
