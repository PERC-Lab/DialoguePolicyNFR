import json
import os
from datetime import datetime, timedelta
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


def parse_timestamps(entries: List[dict]) -> tuple[List[datetime], List[datetime], List[datetime]]:
    """Extract and parse ISO timestamps from conversation entries.
    
    Returns:
        Tuple of (request_timestamps, response_timestamps, all_timestamps)
    """
    request_timestamps = []
    response_timestamps = []
    all_timestamps = []
    
    for entry in entries:
        # Support new format with request_timestamp and response_timestamp
        req_ts = entry.get("request_timestamp")
        resp_ts = entry.get("response_timestamp")
        
        # Support old format with single timestamp (backward compatibility)
        if not req_ts and not resp_ts:
            ts = entry.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    request_timestamps.append(dt)
                    response_timestamps.append(dt)  # Use same timestamp for both
                    all_timestamps.append(dt)
                except ValueError:
                    print(f"Skipping malformed timestamp: {ts}")
            continue
        
        # Parse request timestamp
        if req_ts:
            try:
                req_dt = datetime.fromisoformat(req_ts)
                request_timestamps.append(req_dt)
                all_timestamps.append(req_dt)
            except ValueError:
                print(f"Skipping malformed request_timestamp: {req_ts}")
        
        # Parse response timestamp
        if resp_ts:
            try:
                resp_dt = datetime.fromisoformat(resp_ts)
                response_timestamps.append(resp_dt)
                all_timestamps.append(resp_dt)
            except ValueError:
                print(f"Skipping malformed response_timestamp: {resp_ts}")
    
    return request_timestamps, response_timestamps, all_timestamps


def summarize_session(session_id: str) -> None:
    conversations = load_conversations(CONVERSATIONS_FILE)

    if session_id not in conversations:
        print(f"Session '{session_id}' not found in conversations.")
        return

    entries = conversations[session_id]
    message_count = len(entries)
    print(f"Session ID: {session_id}")
    print(f"Number of conversation entries: {message_count}")
    print()

    request_timestamps, response_timestamps, all_timestamps = parse_timestamps(entries)
    
    if len(all_timestamps) == 0:
        print("No timestamp data found.")
        return
    
    # Show request timestamps
    if request_timestamps:
        print("Request timestamps:")
        for idx, ts in enumerate(request_timestamps, start=1):
            print(f"  {idx}. {ts.isoformat()}")
        print()
    
    # Show response timestamps
    if response_timestamps:
        print("Response timestamps:")
        for idx, ts in enumerate(response_timestamps, start=1):
            print(f"  {idx}. {ts.isoformat()}")
        print()
    
    # Calculate response times (time between request and response for each entry)
    response_times = []
    for entry in entries:
        req_ts = entry.get("request_timestamp")
        resp_ts = entry.get("response_timestamp")
        if req_ts and resp_ts:
            try:
                req_dt = datetime.fromisoformat(req_ts)
                resp_dt = datetime.fromisoformat(resp_ts)
                response_times.append(resp_dt - req_dt)
            except ValueError:
                pass
    
    if response_times:
        print("Response times (time between request and response):")
        for idx, delta in enumerate(response_times, start=1):
            print(f"  {idx}. {delta}")
        print()
        # Calculate average response time
        total_seconds = sum(delta.total_seconds() for delta in response_times)
        avg_seconds = total_seconds / len(response_times)
        avg_response_time = timedelta(seconds=avg_seconds)
        print(f"Average response time: {avg_response_time}")
        print()
    
    # Calculate total duration (from first request to last response)
    if request_timestamps and response_timestamps:
        all_timestamps.sort()
        total_duration = all_timestamps[-1] - all_timestamps[0]
        print(f"Total duration (first request to last response): {total_duration}")
        print()
    
    # Calculate durations between consecutive requests
    if len(request_timestamps) >= 2:
        request_timestamps.sort()
        request_durations = [
            (current - previous)
            for previous, current in zip(request_timestamps, request_timestamps[1:])
        ]
        print("Durations between consecutive requests:")
        for idx, delta in enumerate(request_durations, start=1):
            print(f"  {idx}. {delta}")


if __name__ == "__main__":
    summarize_session(SESSION_ID)
