import os
from copilot_api import CursorAPI

#project_path = os.getcwd()
project_path = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/0/Rocket.Chat.ReactNative"

print(f"Project path: {project_path}\n")

print("Creating new cursor-agent chat...")
try:
    api = CursorAPI(project_path)
    uuid = api.get_uuid()
    print(f"Chat created with UUID: {uuid}\n")
except Exception as e:
    print(f"Error creating chat: {e}")


print("=" * 80)
print("Question 1: What does this app do?")
print("=" * 80)
try:
    response1 = api.ask_cursor_agent("what does this app do")
    print(response1)
    print("\n")
except Exception as e:
    print(f"Error asking question 1: {e}\n")

print("=" * 80)
print("Question 2: What did I just ask?")
print("=" * 80)
try:
    response2 = api.ask_cursor_agent("what did i just asked?")
    print(response2)
    print("\n")
except Exception as e:
    print(f"Error asking question 2: {e}\n")

print(f"Completed! UUID: {uuid}")



