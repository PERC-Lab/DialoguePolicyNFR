import json
import os
from datetime import datetime
from typing import List

# Configure the session we want to inspect.
# Replace this with an existing key from `conversations.json`.
SESSION_ID = "fcf34650-d600-49b7-af52-93b50bab21c2"

CONVERSATIONS_FILE = os.path.join(os.path.dirname(__file__), "conversations.json")


def load_conversations(path: str) -> dict:
    """Read the conversations JSON file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Conversations file not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_timestamps(entries: List[dict]) -> List[datetime]:
    """Extract and parse ISO timestamps from conversation entries."""
    timestamps = []
    for entry in entries:
        ts = entry.get("timestamp")
        if not ts:
            continue
        try:
            timestamps.append(datetime.fromisoformat(ts))
        except ValueError:
            print(f"Skipping malformed timestamp: {ts}")
    return timestamps


def summarize_session(session_id: str) -> None:
    conversations = load_conversations(CONVERSATIONS_FILE)

    if session_id not in conversations:
        print(f"Session '{session_id}' not found in conversations.")
        return

    entries = conversations[session_id]
    message_count = len(entries)
    print(f"Session ID: {session_id}")
    print(f"Number of conversation entries: {message_count}")

    timestamps = parse_timestamps(entries)
    if len(timestamps) < 2:
        print("Not enough timestamp data to compute durations.")
        return

    timestamps.sort()
    print("Message timestamps:")
    for idx, ts in enumerate(timestamps, start=1):
        print(f"  {idx}. {ts.isoformat()}")
    print()
    total_duration = timestamps[-1] - timestamps[0]
    print(f"Total duration: {total_duration}")

    durations = [
        (current - previous)
        for previous, current in zip(timestamps, timestamps[1:])
    ]

    print("Durations between consecutive messages:")
    for idx, delta in enumerate(durations, start=1):
        print(f"  {idx}. {delta}")


if __name__ == "__main__":
    summarize_session(SESSION_ID)
