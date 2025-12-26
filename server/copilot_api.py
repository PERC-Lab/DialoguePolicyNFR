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
        shell_command = (
            f'cd "{self.project_path}" && '
            f'copilot -p "." --model gpt-5.1-codex-max -s --allow-all-tools 2>/dev/null >/dev/null && '
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
                output = result.stdout.strip()[8:]
                if output:
                    return output
                else:
                    raise Exception("Failed to retrieve session ID")
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(f"Failed to create chat: {error_msg}")
        
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout: copilot create-chat took longer than {timeout} seconds")
        except Exception as e:
            raise Exception(f"Error creating copilot chat: {str(e)}")
    
    def ask_cursor_agent(self, message, timeout=600):
        if not self.uuid:
            raise Exception("UUID not initialized. Cannot ask copilot.")
        
        shell_command = (
            f'cd "{self.project_path}" && '
            f'copilot --model gpt-5.1-codex-max --resume "{self.uuid}" -p "{message}" -s --allow-all-tools'
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
    
    def get_uuid(self):
        return self.uuid

