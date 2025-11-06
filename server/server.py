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

@app.route("/api/conversations/<session_id>", methods=["GET"])
def get_conversations(session_id):
    """Retrieve previous conversations for a session ID"""
    if session_id in conversations:
        return jsonify({
            "conversations": conversations[session_id],
            "session_id": session_id
        })
    return jsonify({
        "conversations": [],
        "session_id": session_id
    })

@app.route("/api/hipaa-requirements", methods=["GET"])
def get_hipaa_requirements():
    requirements = [
        {
            "id": 1,
            "title": "Protection Against Unauthorized Uses or Disclosures",
            "description": "The system must protect against any reasonably anticipated uses or disclosures of electronic protected health information that are not permitted or required."
        },
        {
            "id": 2,
            "title": "Access Rights Enforcement",
            "description": "The system shall implement technical policies and procedures for electronic information systems that store ePHI, to ensure that only those persons or software programs that have been granted access rights may access such information."
        },
        {
            "id": 3,
            "title": "Unique User Identification",
            "description": "The system shall assign a unique name and/or number to each user for the purpose of identifying and tracking user identity."
        },
        {
            "id": 4,
            "title": "Emergency Access Procedures",
            "description": "The system shall establish and implement procedures to enable access to necessary electronic protected health information during an emergency."
        },
        {
            "id": 5,
            "title": "Automatic Session Termination",
            "description": "The system shall implement electronic procedures that automatically terminate an electronic session after a predetermined period of inactivity."
        },
        {
            "id": 6,
            "title": "Encryption and Decryption Mechanism",
            "description": "The system shall implement a mechanism to encrypt and decrypt electronic protected health information."
        },
        {
            "id": 7,
            "title": "Transmission Security for ePHI",
            "description": "The system shall implement technical security measures to guard against unauthorized access to ePHI that is transmitted over an electronic communications network. (e.g., The system shall implement a mechanism to encrypt ePHI during electronic transmission whenever deemed appropriate.)"
        },
        {
            "id": 8,
            "title": "Access Granting Policies and Procedures",
            "description": "The system shall implement procedures for granting access to ePHI."
        },
        {
            "id": 9,
            "title": "Log-in Monitoring and Password Management",
            "description": "The system shall implement procedures for monitoring log-in attempts and reporting discrepancies. Implement procedures for creating, changing, and safeguarding passwords."
        },
        {
            "id": 10,
            "title": "Privacy Notice to Individuals",
            "description": "The system shall ensure that individuals receive adequate notice of the uses and disclosures of protected health information that may be made by the covered entity, as well as the individual's rights and the entity's legal duties regarding that information."
        },
        {
            "id": 11,
            "title": "Confidentiality, Integrity, and Availability of ePHI",
            "description": "The system must ensure the confidentiality, integrity, and availability of all electronic protected health information it creates, receives, maintains, or transmits."
        }        
    ]
    return jsonify({"requirements": requirements})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
