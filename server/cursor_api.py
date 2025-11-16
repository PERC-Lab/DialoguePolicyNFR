import subprocess
import os


with open('prompt.txt', 'r') as file:
    initial_prompt = file.read()

class CursorAPI:
    def __init__(self, project_path, uuid=None):
        self.project_path = project_path
        self.uuid = uuid
        
        if not self.uuid:
            self.uuid = self.create_chat()
            self.ask_cursor_agent(initial_prompt)
    
    def create_chat(self, timeout=180):
        shell_command = f'cd "{self.project_path}" && export PATH="$HOME/.local/bin:$PATH" && cursor-agent create-chat'
        
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
                return output
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(f"Failed to create chat: {error_msg}")
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout: cursor-agent create-chat took longer than {timeout} seconds")
        except Exception as e:
            raise Exception(f"Error creating cursor-agent chat: {str(e)}")
    
    def ask_cursor_agent(self, message, timeout=600):
        if not self.uuid:
            raise Exception("UUID not initialized. Cannot ask cursor-agent.")
        
        shell_command = f'cd "{self.project_path}" && export PATH="$HOME/.local/bin:$PATH" && cursor-agent --resume={self.uuid} --print "{message}"'
        
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
                raise Exception(f"Failed to ask cursor-agent: {error_msg}")
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout: cursor-agent took longer than {timeout} seconds to respond")
        except Exception as e:
            raise Exception(f"Error asking cursor-agent: {str(e)}")
    
    def get_uuid(self):
        return self.uuid

