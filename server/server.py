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
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/2/openemr"
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/3/openmrs-module-webservices.rest"
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/0/Rocket.Chat.ReactNative"
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/1/Rocket.Chat"
STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/5/openmrs-core"

STATIC_PROJECT_PATH = "/Users/neo/Desktop/Uni/Collin/05.HIPPA_SW2/2/openemr"

CONVERSATIONS_FILE = "conversations.json"
FEEDBACK_FILE = "nfr_feedback.json"

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

def load_feedback():
    """Load NFR feedback from file"""
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading feedback: {e}")
            return {}
    return {}

def save_feedback(feedback_data):
    """Save NFR feedback to file"""
    try:
        with open(FEEDBACK_FILE, 'w') as f:
            json.dump(feedback_data, f, indent=2)
    except Exception as e:
        print(f"Error saving feedback: {e}")

nfr_feedback = load_feedback()

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

@app.route("/api/nfr-feedback", methods=["POST"])
def submit_nfr_feedback():
    """Save NFR feedback"""
    try:
        data = request.get_json()
        requirement_id = data.get("requirementId")
        session_id = data.get("session_id", "default")
        
        if not requirement_id:
            return jsonify({"error": "requirementId is required"}), 400
        
        feedback_entry = {
            "requirementId": requirement_id,
            "located": data.get("located"),
            "validated": data.get("validated"),
            "otherFeedback": data.get("otherFeedback", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store feedback by session_id, then by requirement ID
        if session_id not in nfr_feedback:
            nfr_feedback[session_id] = {}
        
        if requirement_id not in nfr_feedback[session_id]:
            nfr_feedback[session_id][requirement_id] = []
        
        nfr_feedback[session_id][requirement_id].append(feedback_entry)
        save_feedback(nfr_feedback)
        
        return jsonify({
            "success": True,
            "message": "Feedback saved successfully",
            "feedback": feedback_entry
        }), 201
    
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "error": error_msg
        }), 500

@app.route("/api/nfr-feedback/<session_id>", methods=["GET"])
def get_nfr_feedback(session_id):
    """Get NFR feedback for a specific session"""
    try:
        # Return feedback with completion status for the session
        feedback_status = {}
        
        if session_id in nfr_feedback:
            for req_id, feedback_list in nfr_feedback[session_id].items():
                if feedback_list:
                    # Get the most recent feedback
                    latest = feedback_list[-1]
                    feedback_status[int(req_id)] = {
                        "completed": True,
                        "latestFeedback": latest
                    }
        
        return jsonify({
            "feedback": feedback_status,
            "session_id": session_id
        }), 200
    
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "error": error_msg
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
