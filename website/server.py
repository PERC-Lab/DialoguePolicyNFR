from flask import Flask, render_template, request, jsonify, session
from flask_caching import Cache
import json
import os
import markdown
from chatbot import Chatbot
from datetime import datetime

app = Flask(__name__, template_folder='html_files', static_folder='static')
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Configure cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize chatbot instances (stored by session ID)
chatbots = {}

# File paths
NFR_FILE = 'NFR.json'
CONVERSATION_FILE = 'responses/conversation.json'
NFR_RESPONSES_FILE = 'responses/nfr_responses.json'
SATISFACTION_FILE = 'responses/satisfaction_survey.json'
PRIZE_FILE = 'responses/prize.json'
DEMOGRAPHICS_FILE = 'responses/demographics.json'

def load_json_file(filepath):
    """Load JSON file, return empty dict if file doesn't exist."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json_file(filepath, data):
    """Save data to JSON file."""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_chatbot(uuid=None):
    """Get or create chatbot instance. If UUID provided, restore that chatbot."""
    if uuid:
        # Restore chatbot with provided UUID
        if uuid not in chatbots:
            chatbot = Chatbot()
            chatbot.uuid = uuid  # Set the UUID to the provided one
            chatbots[uuid] = chatbot
            # Load chat history from JSON file
            conversations = load_json_file(CONVERSATION_FILE)
            if uuid in conversations:
                chatbot.chat_history = conversations[uuid]
        return chatbots[uuid]
    else:
        # Create new chatbot (only when no UUID provided)
        chatbot = Chatbot()
        new_uuid = chatbot.get_uuid()
        chatbots[new_uuid] = chatbot
        return chatbot

def get_session_id(uuid=None):
    """Get session ID from chatbot UUID."""
    chatbot = get_chatbot(uuid)
    return chatbot.get_uuid()

@app.route('/')
def index():
    """Show consent form."""
    prolific = request.args.get('id') == 'prolific'
    consent_file = 'consent_forms/consent_prolific.md' if prolific else 'consent_forms/consent_um.md'
    
    with open(consent_file, 'r') as f:
        consent_text = f.read()
    
    consent_html = markdown.markdown(consent_text)
    return render_template('consent.html', consent_html=consent_html, prolific_id=prolific)

@app.route('/consent')
def consent():
    """Show consent form."""
    prolific = request.args.get('id') == 'prolific'
    consent_file = 'consent_forms/consent_prolific.md' if prolific else 'consent_forms/consent_um.md'
    
    with open(consent_file, 'r') as f:
        consent_text = f.read()
    
    consent_html = markdown.markdown(consent_text)
    return render_template('consent.html', consent_html=consent_html, prolific_id=prolific)

@app.route('/tutorial')
def tutorial():
    """Tutorial page."""
    page = request.args.get('page', '1')
    return render_template('tutorial.html', page=page)

@app.route('/evaluation')
def evaluation():
    """Evaluation page with chatbot and NFR form."""
    batch = int(request.args.get('batch', 1))
    return render_template('evaluation.html', batch=batch)

@app.route('/survey')
def survey():
    """Satisfaction survey page."""
    return render_template('survey.html')

@app.route('/prize')
def prize():
    """Prize collection page."""
    prolific = request.args.get('id') == 'prolific'
    return render_template('prize.html', prolific_id=prolific)


def get_nfr_batch_number():
    return 1

# API Routes
@app.route('/api/get_requirements', methods=['GET'])
def get_requirements():
    """Get NFRs for a specific batch (batches are already in the JSON)."""
    batch = int(request.args.get('batch', 1))
    
    with open(NFR_FILE, 'r') as f:
        all_batches = json.load(f)
    
    # NFR.json is now an array of batches (each batch is an array of NFRs)
    if batch <= len(all_batches):
        batch_nfrs = all_batches[batch - 1]
    else:
        batch_nfrs = []
    
    # Calculate total NFRs
    total_nfrs = sum(len(b) for b in all_batches)
    
    return jsonify({
        'nfrs': batch_nfrs,
        'batch': batch,
        'total_batches': len(all_batches),
        'total_nfrs': total_nfrs
    })

@app.route('/api/submit_nfr_feedback', methods=['POST'])
def submit_nfr_feedback():
    """Save NFR feedback. Accepts either single feedback or batch of feedbacks."""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        uuid = data.get('uuid')
        if not uuid:
            return jsonify({'status': 'error', 'message': 'UUID is required'}), 400
        
        session_id = get_session_id(uuid)
        
        # Load existing responses
        responses = load_json_file(NFR_RESPONSES_FILE)
        
        if session_id not in responses:
            responses[session_id] = []
        
        # Check if this is a batch submission (array) or single submission
        if isinstance(data, list):
            # Batch submission - process all items
            batch = data[0].get('batch') if data else None
            # Remove all existing entries for this batch
            responses[session_id] = [
                r for r in responses[session_id] 
                if r.get('batch') != batch
            ]
            # Add all new entries
            responses[session_id].extend(data)
        else:
            # Single submission
            nfr_id = data.get('nfr_id')
            batch = data.get('batch')
            
            # Remove existing entry for this NFR in this batch if it exists
            responses[session_id] = [
                r for r in responses[session_id] 
                if not (r.get('nfr_id') == nfr_id and r.get('batch') == batch)
            ]
            
            # Add new entry
            responses[session_id].append(data)
        
        save_json_file(NFR_RESPONSES_FILE, responses)
        
        if isinstance(data, list):
            return jsonify({'status': 'success', 'count': len(data)})
        else:
            return jsonify({'status': 'success', 'nfr_id': data.get('nfr_id')})
    except Exception as e:
        print(f"Error in submit_nfr_feedback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/submit_batch_feedback', methods=['POST'])
def submit_batch_feedback():
    """Save batch of NFR feedbacks in one request to avoid race conditions."""
    try:
        data_list = request.json
        if not data_list or not isinstance(data_list, list):
            return jsonify({'status': 'error', 'message': 'Array of feedback data required'}), 400
        
        if not data_list:
            return jsonify({'status': 'error', 'message': 'Empty array'}), 400
        
        uuid = data_list[0].get('uuid')
        if not uuid:
            return jsonify({'status': 'error', 'message': 'UUID is required'}), 400
        
        session_id = get_session_id(uuid)
        batch = data_list[0].get('batch')
        
        # Load existing responses
        responses = load_json_file(NFR_RESPONSES_FILE)
        
        if session_id not in responses:
            responses[session_id] = []
        
        # Remove all existing entries for this batch
        responses[session_id] = [
            r for r in responses[session_id] 
            if r.get('batch') != batch
        ]
        
        # Add all new entries
        responses[session_id].extend(data_list)
        save_json_file(NFR_RESPONSES_FILE, responses)
        
        return jsonify({'status': 'success', 'count': len(data_list)})
    except Exception as e:
        print(f"Error in submit_batch_feedback: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/ask_chatbot', methods=['POST'])
def ask_chatbot():
    """Handle chatbot requests."""
    data = request.json
    user_message = data.get('message', '')
    uuid = data.get('uuid')
    
    chatbot = get_chatbot(uuid)
    response = chatbot.ask_chatbot(user_message)
    
    # Save conversation - get the last entry from chat history which has both timestamps
    session_id = chatbot.get_uuid()
    conversations = load_json_file(CONVERSATION_FILE)
    
    if session_id not in conversations:
        conversations[session_id] = []
    
    # Get the last chat entry which has the correct timestamps
    chat_history = chatbot.get_chat_history()
    if chat_history:
        last_entry = chat_history[-1]
        conversations[session_id].append({
            'user_message': last_entry['user_message'],
            'bot_reply': last_entry['bot_reply'],
            'user_time': last_entry['user_time'],
            'bot_time': last_entry['bot_time']
        })
    
    save_json_file(CONVERSATION_FILE, conversations)
    
    # Return response with UUID
    response['uuid'] = session_id
    return jsonify(response)

@app.route('/api/submit_survey', methods=['POST'])
def submit_survey():
    """Save satisfaction survey responses."""
    data = request.json
    uuid = data.get('uuid')
    session_id = get_session_id(uuid)
    
    surveys = load_json_file(SATISFACTION_FILE)
    surveys[session_id] = data
    save_json_file(SATISFACTION_FILE, surveys)
    
    return jsonify({'status': 'success'})

@app.route('/api/submit_prize', methods=['POST'])
def submit_prize():
    """Save prize collection information."""
    data = request.json
    uuid = data.get('uuid')
    session_id = get_session_id(uuid)
    
    prizes = load_json_file(PRIZE_FILE)
    prizes[session_id] = data
    save_json_file(PRIZE_FILE, prizes)
    
    return jsonify({'status': 'success'})

@app.route('/api/submit_demographics', methods=['POST'])
def submit_demographics():
    """Save demographic information."""
    data = request.json
    uuid = data.get('uuid')
    session_id = get_session_id(uuid)
    
    demographics = load_json_file(DEMOGRAPHICS_FILE)
    demographics[session_id] = {
        **data,
        'timestamp': datetime.now().isoformat()
    }
    save_json_file(DEMOGRAPHICS_FILE, demographics)
    
    return jsonify({'status': 'success'})

@app.route('/api/get_or_create_uuid', methods=['GET', 'POST'])
def get_or_create_uuid():
    """Get existing UUID from request or create new one."""
    if request.method == 'POST':
        data = request.json
        uuid = data.get('uuid')
        if uuid:
            # Always restore/validate the provided UUID
            # Even if it doesn't exist in data files yet, it might be a new session
            # Just restore the chatbot with this UUID
            get_chatbot(uuid)
            return jsonify({'uuid': uuid})
    
    # Create new UUID (GET request - only called from consent page)
    chatbot = get_chatbot()
    new_uuid = chatbot.get_uuid()
    return jsonify({'uuid': new_uuid})

@app.route('/api/load_chat_history', methods=['POST'])
def load_chat_history():
    """Load chat history for a given UUID."""
    data = request.json
    uuid = data.get('uuid')
    if not uuid:
        return jsonify({'history': []})
    
    conversations = load_json_file(CONVERSATION_FILE)
    history = conversations.get(uuid, [])
    return jsonify({'history': history})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
