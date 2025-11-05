from flask import Flask, request, jsonify
from flask_cors import CORS
from cursor_api import CursorAPI
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/0/Rocket.Chat.ReactNative"
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/4/iTrust"
CONVERSATIONS_FILE = "conversations.json"

cursor_sessions = set()

def load_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r') as f:
                data = json.load(f)
                cursor_sessions.update(data.keys())
                return data
        except Exception as e:
            print(f"Error loading conversations: {e}")
            return {}
    return {}

def save_conversations(conversations):
    try:
        with open(CONVERSATIONS_FILE, 'w') as f:
            json.dump(conversations, f, indent=2)
    except Exception as e:
        print(f"Error saving conversations: {e}")

conversations = load_conversations()

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    
    try:
        if session_id == "default" or session_id not in cursor_sessions:
            cursor_api = CursorAPI(STATIC_PROJECT_PATH)
            session_id = cursor_api.get_uuid()
            cursor_sessions.add(session_id)
            conversations[session_id] = []
        else:
            cursor_api = CursorAPI(STATIC_PROJECT_PATH, uuid=session_id)
            if session_id not in conversations:
                conversations[session_id] = []
        
        reply = cursor_api.ask_cursor_agent(user_message)
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_reply": reply
        }
        conversations[session_id].append(conversation_entry)
        
        save_conversations(conversations)
        
        return jsonify({
            "reply": reply,
            "session_id": session_id
        })
    
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "reply": f"Error: {error_msg}",
            "session_id": session_id
        }), 500

@app.route("/api/hipaa-requirements", methods=["GET"])
def get_hipaa_requirements():
    requirements = [
        {
            "id": 1,
            "title": "Administrative Safeguards",
            "description": "Security management process, assigned security responsibility, workforce security, information access management, security awareness and training, security incident procedures, contingency plan, evaluation, business associate contracts and other arrangements."
        },
        {
            "id": 2,
            "title": "Physical Safeguards",
            "description": "Facility access controls, workstation use, workstation security, and device and media controls to restrict physical access to ePHI."
        },
        {
            "id": 3,
            "title": "Technical Safeguards",
            "description": "Access control, audit controls, integrity controls, transmission security to protect and control access to ePHI."
        },
        {
            "id": 4,
            "title": "Encryption of ePHI",
            "description": "Encrypt ePHI both at rest (stored data) and in transit (data being transmitted) to protect against unauthorized access."
        },
        {
            "id": 5,
            "title": "Access Control",
            "description": "Implement unique user identification, emergency access procedures, automatic logoff, and encryption and decryption of ePHI."
        },
        {
            "id": 6,
            "title": "Audit Controls",
            "description": "Implement hardware, software, and/or procedural mechanisms to record and examine access and other activity in information systems that contain or use ePHI."
        },
        {
            "id": 7,
            "title": "Integrity Controls",
            "description": "Implement policies and procedures to ensure ePHI is not improperly altered or destroyed."
        },
        {
            "id": 8,
            "title": "Transmission Security",
            "description": "Implement technical security measures to guard against unauthorized access to ePHI that is being transmitted over an electronic communications network."
        },
        {
            "id": 9,
            "title": "Privacy Notice",
            "description": "Provide patients with a notice of privacy practices that explains how their health information is used and disclosed, and their rights regarding their health information."
        },
        {
            "id": 10,
            "title": "Minimum Necessary Rule",
            "description": "When using or disclosing PHI or when requesting PHI from another covered entity, make reasonable efforts to limit PHI to the minimum necessary to accomplish the intended purpose."
        },
        {
            "id": 11,
            "title": "Business Associate Agreements",
            "description": "Have written contracts or other arrangements with business associates that ensure they appropriately safeguard PHI."
        },
        {
            "id": 12,
            "title": "Breach Notification",
            "description": "Notify affected individuals, HHS, and in some cases the media, if there is a breach of unsecured PHI."
        },
        {
            "id": 13,
            "title": "Patient Rights",
            "description": "Provide patients with rights to access, amend, and receive an accounting of disclosures of their PHI, and the right to request restrictions on certain uses and disclosures."
        },
        {
            "id": 14,
            "title": "Workforce Training",
            "description": "Train all workforce members on HIPAA policies and procedures, including security awareness training and periodic updates."
        },
        {
            "id": 15,
            "title": "Risk Assessment",
            "description": "Conduct a thorough risk assessment to identify potential threats and vulnerabilities to the confidentiality, integrity, and availability of ePHI."
        }
    ]
    return jsonify({"requirements": requirements})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
