import subprocess
import os
import shlex
import re
from datetime import datetime
from typing import Dict, List, Optional

STATIC_PROJECT_PATH = "/Users/neo/Desktop/NFR/new/website-server-copy/iTrust/iTrust"
#STATIC_PROJECT_PATH = "/root/iTrust/iTrust"
MODEL = f"gpt-5.1-codex-max"
MODEL = f"gpt-5-mini"
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
    
    def _extract_uuid_from_text(self, text: str) -> Optional[str]:
        uuid_match = re.search(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', text)
        return uuid_match.group(0) if uuid_match else None

    def _latest_session_state_uuid(self) -> Optional[str]:
        # ls -t ~/.copilot/session-state | head -n1
        session_state_dir = os.path.expanduser('~/.copilot/session-state')
        if not os.path.isdir(session_state_dir):
            return None
        entries = [os.path.join(session_state_dir, name) for name in os.listdir(session_state_dir)
                   if not name.startswith('process')]
        entries = [e for e in entries if os.path.isfile(e) or os.path.isdir(e)]
        if not entries:
            return None
        latest = max(entries, key=os.path.getmtime)
        base = os.path.basename(latest)
        if base.endswith('.jsonl'):
            base = base[:-6]
        return base

    def _latest_process_log_uuid(self) -> Optional[str]:
        logs_dir = os.path.expanduser('~/.copilot/logs')
        if not os.path.isdir(logs_dir):
            return None
        logs = [os.path.join(logs_dir, name) for name in os.listdir(logs_dir) if name.startswith('process-')]
        if not logs:
            return None
        latest = max(logs, key=os.path.getmtime)
        try:
            with open(latest, 'r') as f:
                content = f.read()
            uuid = self._extract_uuid_from_text(content)
            if uuid and uuid.startswith('session-'):
                uuid = uuid[8:]
            return uuid
        except Exception:
            return None

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
            f'copilot -p {escaped_prompt} --model {MODEL} -s --allow-all-tools'
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
            print('here')
            
            if result.returncode == 0:
                '''
                # Prefer UUID from CLI output if available
                uuid = self._extract_uuid_from_text(result.stdout or '') or self._extract_uuid_from_text(result.stderr or '')
                if not uuid:
                    # Fallback to session-state (works on both folder and .jsonl formats)
                    uuid = self._latest_session_state_uuid()
                print('here2')
                if not uuid:
                    # Final fallback: scrape newest process log
                    uuid = self._latest_process_log_uuid()
                print('here3')
                '''
                uuid = self._latest_session_state_uuid()
                if uuid:
                    self.chat_history = []
                    return uuid
                raise Exception("Failed to retrieve session ID from copilot")
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
        print(f"Executing copilot command with session UUID: {self.uuid}")
        print(f"Executing copilot command with session UUID: {escaped_uuid}")
        
        shell_command = (
            f'cd {escaped_path} && '
            f'copilot --model {MODEL} --resume {escaped_uuid} -p {escaped_message} -s --allow-all-tools'
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
