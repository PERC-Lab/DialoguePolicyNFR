from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_caching import Cache
import json
import os
import markdown
from chatbot import Chatbot
from datetime import datetime
import hashlib
import math
import random
from functools import wraps

app = Flask(__name__, template_folder='html_files', static_folder='static')
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Configure cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize chatbot instances (stored by session ID)
chatbots = {}

# Admin authentication
# Get admin password from environment variable or use default (CHANGE IN PRODUCTION!)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'perc123Perclab')  # Change this default!
ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

def require_admin(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# File paths
NFR_FILE = 'NFR.json'
CONVERSATION_FILE = 'responses/conversation.json'
NFR_RESPONSES_FILE = 'responses/nfr_responses.json'
SATISFACTION_FILE = 'responses/satisfaction_survey.json'
PRIZE_FILE = 'responses/prize.json'
DEMOGRAPHICS_FILE = 'responses/demographics.json'
BATCH_ASSIGNMENTS_FILE = 'responses/user_batch_assignments.json'
FORCED_NFRS_FILE = 'forced.json'
GATE_ANSWERS_FILE = 'responses/gate_answers.json'

# How many NFRs should force an independent assessment per participant
FORCED_ASSESSMENT_RATIO = 0.2  # 40% of NFRs in the batch
MIN_FORCED_ASSESSMENTS = 1     # Always force at least one


def build_batch_participants(assignments):
    """Return mapping of actual batch -> ordered list of participant UUIDs."""
    participants_by_batch = {}
    for user_uuid, batches in assignments.items():
        for batch_num in batches:
            participants_by_batch.setdefault(batch_num, [])
            if user_uuid not in participants_by_batch[batch_num]:
                participants_by_batch[batch_num].append(user_uuid)
    return participants_by_batch


def get_participant_index(uuid, actual_batch, assignments):
    """Return 1-based participant index (1 or 2) within a batch for a UUID."""
    participants_by_batch = build_batch_participants(assignments)
    participants = participants_by_batch.get(actual_batch, [])
    if uuid in participants:
        return participants.index(uuid) + 1
    return None


def compute_forced_assessment_nfrs(nfr_list, actual_batch, uuid, participant_index):
    """Deterministically pick a subset of NFR IDs that must include independent assessments."""
    if not nfr_list or not uuid:
        return []
    idx = participant_index or 1
    rng = random.Random()
    rng.seed(f"force-{actual_batch}-{idx}-{uuid}")
    desired = max(MIN_FORCED_ASSESSMENTS, math.ceil(len(nfr_list) * FORCED_ASSESSMENT_RATIO))
    desired = min(desired, len(nfr_list))
    selected = rng.sample(nfr_list, k=desired)
    return [nfr.get('id') for nfr in selected if isinstance(nfr, dict) and 'id' in nfr]


def compute_peer_required_nfrs(actual_batch, participant_index, assignments):
    """If current user is participant 2, find NFRs where participant 1 disagreed but gave no assessment."""
    empty = {'q1': [], 'q2': [], 'q3': []}
    if participant_index != 2:
        return empty

    participants_by_batch = build_batch_participants(assignments)
    participants = participants_by_batch.get(actual_batch, [])
    if not participants:
        return empty

    primary_uuid = participants[0]
    responses = load_json_file(NFR_RESPONSES_FILE)
    peer_responses = responses.get(primary_uuid, [])
    peer_required = {'q1': set(), 'q2': set(), 'q3': set()}

    for entry in peer_responses:
        if entry.get('batch') != actual_batch:
            continue
        nfr_id = entry.get('nfr_id')
        for q_key in ('q1', 'q2', 'q3'):
            agreement = entry.get(f"{q_key}_agreement")
            own_assessment = (entry.get(f"{q_key}_own_assessment") or '').strip()
            if agreement and agreement != 'Agree' and not own_assessment:
                peer_required[q_key].add(nfr_id)

    return {k: sorted([n for n in v if n is not None]) for k, v in peer_required.items()}

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

def assign_batches_to_user(uuid):
    """Assign 3 batches to a new user, ensuring each batch has exactly 2 users.
    Assigns first available batches (not randomly)."""

    #TODO remove this after testing
    return [1, 2, 3]
    assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
    
    # If user already has assignments, return them
    if uuid in assignments:
        return assignments[uuid]
    
    # Load total number of batches
    with open(NFR_FILE, 'r') as f:
        all_batches = json.load(f)
    total_batches = len(all_batches)
    
    # Count how many users are assigned to each batch
    batch_user_count = {}
    for user_uuid, user_batches in assignments.items():
        for batch_num in user_batches:
            batch_user_count[batch_num] = batch_user_count.get(batch_num, 0) + 1
    
    # Find first 3 batches that have less than 2 users (in order)
    assigned = []
    for batch_num in range(1, total_batches + 1):
        if batch_user_count.get(batch_num, 0) < 2:
            assigned.append(batch_num)
            if len(assigned) == 3:
                break
    
    # If we don't have enough available batches, assign remaining from the beginning
    if len(assigned) < 3:
        for batch_num in range(1, total_batches + 1):
            if batch_num not in assigned:
                assigned.append(batch_num)
                if len(assigned) == 3:
                    break
    
    # Sort assigned batches
    assigned = sorted(assigned[:3])
    
    # Save assignments
    assignments[uuid] = assigned
    save_json_file(BATCH_ASSIGNMENTS_FILE, assignments)
    
    return assigned

def get_user_assigned_batch(uuid, requested_batch_num):
    """Get the actual batch number for a user's requested batch (1, 2, or 3)."""
    assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
    
    if uuid not in assignments:
        # No assignments yet, assign them
        assignments[uuid] = assign_batches_to_user(uuid)
    
    user_batches = assignments[uuid]
    
    # requested_batch_num is 1-indexed (1, 2, or 3)
    if 1 <= requested_batch_num <= len(user_batches):
        return user_batches[requested_batch_num - 1]
    else:
        # Invalid batch number, return first assigned batch
        return user_batches[0] if user_batches else 1

def get_chatbot(uuid=None):
    """Get or create chatbot instance. If UUID provided, restore that chatbot."""
    if uuid:
        # Restore chatbot with provided UUID
        if uuid not in chatbots:
            # Pass UUID to constructor to resume the existing copilot session
            chatbot = Chatbot(uuid=uuid)
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
    
    # Convert markdown to HTML with extensions for proper list rendering
    try:
        consent_html = markdown.markdown(consent_text, extensions=['extra', 'nl2br'])
    except:
        # Fallback if extensions not available
        consent_html = markdown.markdown(consent_text)
    return render_template('consent.html', consent_html=consent_html, prolific_id=prolific)

@app.route('/consent')
def consent():
    """Show consent form."""
    prolific = request.args.get('id') == 'prolific'
    consent_file = 'consent_forms/consent_prolific.md' if prolific else 'consent_forms/consent_um.md'
    
    with open(consent_file, 'r') as f:
        consent_text = f.read()
    
    # Convert markdown to HTML with extensions for proper list rendering
    try:
        consent_html = markdown.markdown(consent_text, extensions=['extra', 'nl2br'])
    except:
        # Fallback if extensions not available
        consent_html = markdown.markdown(consent_text)
    return render_template('consent.html', consent_html=consent_html, prolific_id=prolific)

@app.route('/tutorial')
def tutorial():
    """Tutorial page."""
    page = request.args.get('page', '1')
    # Open tutorial modal if requested
    show_modal = request.args.get('modal') == 'true'
    return render_template('tutorial.html', page=page, show_modal=show_modal)

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
    """Prize collection page. Non-Prolific: show email form only if fewer than 15 emails collected."""
    prolific = request.args.get('id') == 'prolific'
    email_prize_available = True
    if not prolific:
        prizes = _normalize_prizes(load_json_file(PRIZE_FILE))
        email_prize_available = len(prizes.get('emails', [])) < 15
    return render_template('prize.html', prolific_id=prolific, email_prize_available=email_prize_available)

@app.route('/complete')
def complete():
    """Study completion page."""
    prolific = request.args.get('id') == 'prolific'
    return render_template('completion.html', prolific_id=prolific)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == ADMIN_PASSWORD_HASH:
            session['admin_authenticated'] = True
            next_url = request.args.get('next', url_for('admin'))
            return redirect(next_url)
        else:
            return render_template('admin_login.html', error='Invalid password')
    
    # If already authenticated, redirect to admin
    if session.get('admin_authenticated'):
        return redirect(url_for('admin'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout."""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@require_admin
def admin():
    """Admin dashboard page."""
    return render_template('admin.html')


def get_nfr_batch_number():
    return 1

# API Routes
@app.route('/api/get_requirements', methods=['GET'])
def get_requirements():
    """Get NFRs for a specific batch. Maps user's requested batch (1-3) to their assigned batch."""
    requested_batch = int(request.args.get('batch', 1))
    uuid = request.args.get('uuid')
    
    # Get user's assigned batches
    assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
    if uuid:
        if uuid not in assignments:
            # Assign batches to new user
            assign_batches_to_user(uuid)
            assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
        
        user_batches = assignments.get(uuid, [])
        
        # Map requested batch (1-3) to actual assigned batch
        if 1 <= requested_batch <= len(user_batches):
            actual_batch = user_batches[requested_batch - 1]
        else:
            actual_batch = user_batches[0] if user_batches else 1
    else:
        # No UUID provided, use requested batch directly
        actual_batch = requested_batch
    
    with open(NFR_FILE, 'r') as f:
        all_batches = json.load(f)
    
    # NFR.json is now an array of batches (each batch is an array of NFRs)
    if actual_batch <= len(all_batches):
        batch_nfrs = all_batches[actual_batch - 1].copy()  # Make a copy to avoid modifying original
    else:
        batch_nfrs = []

    # Insert attention questions based on requested batch (user's batch 1, 2, or 3)
    # Positions are 1-indexed: "after 6" means after the 6th item (insert at index 6 in 0-indexed)
    attention_positions = {
        1: [6, 8],  # Batch 1: after NFR 6 and 8
        2: [5, 9],  # Batch 2: after NFR 5 and 9
        3: [4, 9]   # Batch 3: after NFR 4 and 9
    }
    
    if requested_batch in attention_positions:
        positions = attention_positions[requested_batch]
        # Sort positions in descending order to insert from end to beginning
        # This avoids index shifting issues when inserting multiple items
        positions_sorted = sorted(positions, reverse=True)
        
        attention_counter = 1
        for pos in positions_sorted:
            # pos is 1-indexed position (after NFR 6 means after index 5, so insert at index 6)
            # Convert to 0-indexed: pos becomes the insertion index
            insert_index = pos
            if insert_index <= len(batch_nfrs) and insert_index > 0:
                # Get the title and id from the previous NFR (at index pos-1)
                previous_nfr = batch_nfrs[insert_index - 1]
                previous_title = previous_nfr.get('title', 'Attention Check')
                previous_id = previous_nfr.get('id')
                
                attention_nfr = {
                    'id': previous_id,
                    'title': previous_title,
                    'description': 'Please leave this NFR\'s checkbox unchecked to confirm you are reading carefully.',
                    'is_attention_question': True
                }
                batch_nfrs.insert(insert_index, attention_nfr)
                attention_counter += 1

    participant_index = get_participant_index(uuid, actual_batch, assignments) if uuid else None
    forced_assessment_nfr_ids = compute_forced_assessment_nfrs(batch_nfrs, actual_batch, uuid, participant_index)
    peer_required_by_question = compute_peer_required_nfrs(actual_batch, participant_index, assignments) if uuid else {'q1': [], 'q2': [], 'q3': []}
    forced_nfrs = load_json_file(FORCED_NFRS_FILE)
    if not isinstance(forced_nfrs, list):
        forced_nfrs = []
    
    # Calculate total NFRs
    total_nfrs = sum(len(b) for b in all_batches)
    
    return jsonify({
        'nfrs': batch_nfrs,
        'batch': requested_batch,  # Return requested batch (1-3) for display
        'actual_batch': actual_batch,  # Return actual batch number
        'total_batches': len(user_batches) if uuid and uuid in assignments else len(all_batches),
        'total_nfrs': total_nfrs,
        'assigned_batches': user_batches if uuid and uuid in assignments else [],
        'participant_index': participant_index,
        'force_assessment_nfr_ids': forced_assessment_nfr_ids,
        'peer_required_by_question': peer_required_by_question,
        'forced_nfrs': forced_nfrs
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
        requested_batch = data_list[0].get('batch')  # This is 1, 2, or 3
        
        # Get actual batch number from assignments
        assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
        if uuid in assignments:
            user_batches = assignments[uuid]
            if 1 <= requested_batch <= len(user_batches):
                actual_batch = user_batches[requested_batch - 1]
            else:
                actual_batch = user_batches[0] if user_batches else requested_batch
        else:
            actual_batch = requested_batch
        
        # Load existing responses
        responses = load_json_file(NFR_RESPONSES_FILE)
        
        if session_id not in responses:
            responses[session_id] = []
        
        # Remove all existing entries for this actual batch
        responses[session_id] = [
            r for r in responses[session_id] 
            if r.get('batch') != actual_batch
        ]
        
        # Update all entries to use actual batch number
        for entry in data_list:
            entry['batch'] = actual_batch
        
        # Add all new entries
        responses[session_id].extend(data_list)
        save_json_file(NFR_RESPONSES_FILE, responses)

        # Update forced NFRs: force when user disagrees on Q2 or Q3 and leaves that question without an assessment
        #TODO
        '''
        loaded_forced = load_json_file(FORCED_NFRS_FILE)
        forced_nfrs = set(loaded_forced) if isinstance(loaded_forced, list) else set()
        additions = 0

        for entry in data_list:
            nfr_id = entry.get('nfr_id')
            if nfr_id is None:
                continue

            q2_agree = entry.get('q2_agreement')
            q3_agree = entry.get('q3_agreement')
            q2_own = (entry.get('q2_own_assessment') or '').strip()
            q3_own = (entry.get('q3_own_assessment') or '').strip()

            disagree_q2 = bool(q2_agree and q2_agree != 'Agree')
            disagree_q3 = bool(q3_agree and q3_agree != 'Agree')
            disagrees = disagree_q2 or disagree_q3
            misssing = not q2_own or not q3_own
            #missing_q2 = disagree_q2 and not q2_own
            #missing_q3 = disagree_q3 and not q3_own

            should_force = disagrees and misssing

            if should_force:
                if additions < 2 and nfr_id not in forced_nfrs:
                    forced_nfrs.add(nfr_id)
                    additions += 1
            else:
                forced_nfrs.discard(nfr_id)

        # Enforce a hard cap of 2 forced NFRs
        if len(forced_nfrs) > 2:
            forced_nfrs = set(sorted(forced_nfrs)[:2])

        save_json_file(FORCED_NFRS_FILE, sorted(forced_nfrs))
        '''
        
        
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

def _normalize_prizes(prizes):
    """Ensure prizes has 'prolific' (dict keyed by session_id) and 'emails' (list)."""
    if isinstance(prizes, dict) and 'prolific' in prizes and 'emails' in prizes:
        return prizes
    # Old format: whole dict was keyed by session_id (prolific only)
    return {'prolific': prizes if isinstance(prizes, dict) else {}, 'emails': []}


@app.route('/api/submit_prize', methods=['POST'])
def submit_prize():
    """Save prize collection information. Prolific: keyed by session_id. Non-Prolific: email appended to list (no uuid)."""
    data = request.json
    prizes = _normalize_prizes(load_json_file(PRIZE_FILE))

    if data.get('type') == 'prolific_id':
        uuid = data.get('uuid')
        session_id = get_session_id(uuid)
        prizes['prolific'][session_id] = data
    else:
        # Non-Prolific: save email in list only, do not assign uuid
        email = (data.get('identifier') or '').strip()
        if email:
            prizes.setdefault('emails', []).append(email)
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
    """Get existing UUID from request or create new one. Assigns batches when creating new UUID."""
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
    
    # Assign batches to the new user
    assign_batches_to_user(new_uuid)
    
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


@app.route('/api/submit_gate_answer', methods=['POST'])
def submit_gate_answer():
    """Save the gate question answer (user's explanation of a random NFR)."""
    try:
        data = request.json
        uuid_val = data.get('uuid')
        batch = data.get('batch')
        nfr_id = data.get('nfr_id')
        answer = (data.get('answer') or '').strip()
        if not uuid_val:
            return jsonify({'status': 'error', 'message': 'UUID is required'}), 400
        if answer == '':
            return jsonify({'status': 'error', 'message': 'Answer is required'}), 400
        session_id = get_session_id(uuid_val)
        gate_answers = load_json_file(GATE_ANSWERS_FILE)
        if session_id not in gate_answers:
            gate_answers[session_id] = {}
        batch_key = str(batch)
        if batch_key not in gate_answers[session_id]:
            gate_answers[session_id][batch_key] = {}
        gate_answers[session_id][batch_key][str(nfr_id)] = {
            'nfr_id': nfr_id,
            'batch': batch,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        }
        save_json_file(GATE_ANSWERS_FILE, gate_answers)
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in submit_gate_answer: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/admin/data', methods=['GET'])
@require_admin
def get_admin_data():
    """Get all admin data for the dashboard."""
    try:
        # Load all data files
        conversations = load_json_file(CONVERSATION_FILE)
        nfr_responses = load_json_file(NFR_RESPONSES_FILE)
        surveys = load_json_file(SATISFACTION_FILE)
        demographics = load_json_file(DEMOGRAPHICS_FILE)
        prizes = load_json_file(PRIZE_FILE)
        prizes = _normalize_prizes(prizes)
        batch_assignments = load_json_file(BATCH_ASSIGNMENTS_FILE)
        gate_answers = load_json_file(GATE_ANSWERS_FILE)
        
        # Calculate statistics
        # Get unique participants from all data sources (prolific prizes keyed by session_id; emails are a list)
        all_uuids = set()
        all_uuids.update(conversations.keys())
        all_uuids.update(nfr_responses.keys())
        all_uuids.update(surveys.keys())
        all_uuids.update(demographics.keys())
        all_uuids.update(prizes.get('prolific', {}).keys())
        all_uuids.update(batch_assignments.keys())
        all_uuids.update(gate_answers.keys())
        
        total_conversations = sum(len(msgs) for msgs in conversations.values())
        total_nfr_responses = sum(len(responses) for responses in nfr_responses.values())
        total_prizes_count = len(prizes.get('prolific', {})) + len(prizes.get('emails', []))
        
        stats = {
            'total_participants': len(all_uuids),
            'total_conversations': len(conversations),
            'total_conversation_messages': total_conversations,
            'total_nfr_responses': total_nfr_responses,
            'total_surveys': len(surveys),
            'total_demographics': len(demographics),
            'total_prizes': total_prizes_count,
            'total_batch_assignments': len(batch_assignments),
            'total_gate_answers': len(gate_answers)
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'conversations': conversations,
            'nfr_responses': nfr_responses,
            'surveys': surveys,
            'demographics': demographics,
            'prizes': prizes,
            'batch_assignments': batch_assignments,
            'gate_answers': gate_answers
        })
    except Exception as e:
        print(f"Error in get_admin_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/clear_all_data', methods=['POST'])
@require_admin
def clear_all_data():
    """Clear all response data files. This is a destructive operation."""
    try:
        # Clear all response files by saving empty dictionaries
        save_json_file(CONVERSATION_FILE, {})
        save_json_file(NFR_RESPONSES_FILE, {})
        save_json_file(SATISFACTION_FILE, {})
        save_json_file(DEMOGRAPHICS_FILE, {})
        save_json_file(PRIZE_FILE, {'prolific': {}, 'emails': []})
        save_json_file(BATCH_ASSIGNMENTS_FILE, {})
        save_json_file(GATE_ANSWERS_FILE, {})
        
        # Clear in-memory chatbot instances
        chatbots.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'All data has been cleared successfully'
        })
    except Exception as e:
        print(f"Error in clear_all_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
