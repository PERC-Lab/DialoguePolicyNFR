# HIPAA Compliance Assistant (HIPAAC)

A VS Code extension that helps verify HIPAA compliance by providing an interactive chatbot assistant and a comprehensive checklist of Non-Functional Requirements (NFRs).

## Features

### Interactive Chat Assistant
- Chat with an AI assistant to verify HIPAA compliance
- Ask questions about specific requirements and get detailed responses
- Session-based conversations that persist across VS Code sessions

### NFR Checklist
- View and evaluate HIPAA requirements organized by sections
- Navigate through multiple pages of requirements using pagination
- Submit detailed feedback for each requirement including:
  - Satisfaction level assessment
  - Reasoning and code locations
  - Agreement verification with chatbot responses
  - Optional own assessments when partially agreeing or disagreeing

### Session Management
- Clear session ID command to start fresh conversations
- Automatic session tracking for continuity

## Requirements

This extension requires a backend server to be running. The server should be accessible at `localhost:3000` and provide the following endpoints:

- `/api/ask` - For chat interactions
- `/api/hipaa-requirements` - For fetching NFR requirements
- `/api/nfr-feedback` - For submitting feedback
- `/api/nfr-feedback/<session_id>` - For retrieving saved feedback
- `/api/conversations/<session_id>` - For retrieving conversation history

Make sure the backend server is running before using the extension.

## Usage

1. **Start the Backend Server**: Ensure the Flask server is running on port 3000
2. **Open the Extension**: Click on the "HIPAA Compliance" icon in the activity bar
3. **Use the Chat Assistant**: 
   - Go to the "Assistant" tab to chat with the AI about HIPAA compliance
   - Ask questions about specific requirements or general compliance topics
4. **Review NFR Checklist**:
   - Go to the "List of NFRs" tab to see all requirements
   - Navigate between pages using Previous/Next buttons
   - Fill out the feedback form for each requirement
   - Submit your feedback (all fields are mandatory)

## Extension Settings

This extension does not currently add any VS Code settings.

## Commands

- `hipaac.clearSession`: Clear the current session ID to start a new session

## Known Issues

None at this time.

## Release Notes

### 0.0.1

Initial release of HIPAA Compliance Assistant:
- Interactive chat assistant for HIPAA compliance verification
- Comprehensive NFR checklist with pagination
- Feedback submission system with validation
- Session management

---

**Enjoy using the HIPAA Compliance Assistant!**
