#!/usr/bin/env python3
"""
Simple example of using cursor-agent from Python
"""
from cursor_api import ask_cursor_agent

# Ask questions
answer1 = ask_cursor_agent("what does this app do?")
print("="*80)
print("ANSWER 1:")
print("="*80)
print(answer1)
print()

answer2 = ask_cursor_agent("what are the main files?")
print("="*80)
print("ANSWER 2:")
print("="*80)
print(answer2)
print()

# Use JSON format
answer_json = ask_cursor_agent("list the main components", output_format="json")
print("="*80)
print("JSON ANSWER:")
print("="*80)
print(answer_json)

