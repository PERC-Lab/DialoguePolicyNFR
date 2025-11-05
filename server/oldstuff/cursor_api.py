#!/usr/bin/env python3
"""
Simple Python wrapper for cursor-agent CLI
"""
import subprocess
import os
import glob
import sys

# Find the cursor-agent installation directory
def find_cursor_agent_dir():
    """Find the cursor-agent installation directory"""
    home = os.environ.get('HOME', '')
    glob_pattern = f"{home}/.local/share/cursor-agent/versions/*/"
    dirs = glob.glob(glob_pattern)
    if dirs:
        return sorted(dirs)[-1]
    return None

cursor_agent_dir = find_cursor_agent_dir()

def ask_cursor_agent(question, working_dir=None, output_format="text", timeout=180):
    """
    Ask a question to cursor-agent and get the response.
    
    Args:
        question: The question to ask
        working_dir: Optional working directory
        output_format: "text", "json", or "stream-json"
        timeout: Timeout in seconds
    
    Returns:
        The response from cursor-agent
    """
    # Try cursor-agent command first
    cmd = ["cursor-agent", "--print", "--output-format", output_format, question]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"cursor-agent command failed (code: {result.returncode})")
            if result.stderr:
                print(f"stderr: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("cursor-agent timed out, trying direct Node path...")
    
    except FileNotFoundError:
        print("cursor-agent not found in PATH, trying direct Node path...")
    
    # Fallback: direct Node execution
    if cursor_agent_dir:
        node_bin = f"{cursor_agent_dir}/node"
        index_js = f"{cursor_agent_dir}/index.js"
        cmd = [node_bin, "--use-system-ca", index_js, "--print", "--output-format", output_format, question]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            error_msg = result.stderr if result.stderr else "Unknown error"
            raise Exception(f"Failed: {error_msg}")
    else:
        raise Exception("Could not find cursor-agent installation")

if __name__ == "__main__":
    # Example usage
    question = sys.argv[1] if len(sys.argv) > 1 else "what does this app do?"
    print(f"Question: {question}\n")
    
    try:
        answer = ask_cursor_agent(question)
        print("="*80)
        print("ANSWER:")
        print("="*80)
        print(answer)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

