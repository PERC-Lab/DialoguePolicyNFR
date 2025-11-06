const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const http = require('http');

function activate(context) {
  const chatProvider = new ChatViewProvider(context.extensionUri, context);
  const checklistProvider = new ChecklistViewProvider(context.extensionUri);
  
  // Register command to clear session ID
  const clearSessionCommand = vscode.commands.registerCommand('hipaac.clearSession', () => {
    chatProvider._clearSessionId();
    vscode.window.showInformationMessage('Session ID cleared. New session will be created on next message.');
  });
  
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, chatProvider),
    vscode.window.registerWebviewViewProvider(ChecklistViewProvider.viewType, checklistProvider),
    clearSessionCommand
  );
}

class ChatViewProvider {
  static viewType = 'chatView';

  constructor(extensionUri, context) {
    this._extensionUri = extensionUri;
    this._context = context;
    this._sessionId = this._getSessionId();
  }

  _getSessionId() {
    const sessionKey = 'hipaaSessionId';
    let sessionId = this._context.globalState.get(sessionKey);
    if (!sessionId) {
      sessionId = 'default';
    }
    return sessionId;
  }

  _saveSessionId(sessionId) {
    const sessionKey = 'hipaaSessionId';
    this._context.globalState.update(sessionKey, sessionId);
    this._sessionId = sessionId;
  }

  _clearSessionId() {
    const sessionKey = 'hipaaSessionId';
    this._context.globalState.update(sessionKey, undefined);
    this._sessionId = 'default';
  }

  resolveWebviewView(webviewView) {
    webviewView.webview.options = {
      enableScripts: true
    };

    webviewView.webview.html = this._getHtmlForWebview();
    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.type === 'userResponse') {
        const response = await this._sendToBackend(message.text);
        webviewView.webview.postMessage({ type: 'backendResponse', text: response });
      } else if (message.type === 'loadConversations') {
        // Webview is requesting conversations (on initial load or restore)
        await this._loadPreviousConversations(webviewView);
      }
    });
  }

  async _sendToBackend(userMessage) {
    return new Promise((resolve) => {
      const postData = JSON.stringify({ 
        message: userMessage,
        session_id: this._sessionId
      });
      
      const options = {
        hostname: 'localhost',
        port: 3000,
        path: '/api/ask',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData)
        }
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            // If server returned a new session_id, save it
            if (json.session_id && json.session_id !== this._sessionId) {
              this._saveSessionId(json.session_id);
            }
            resolve(json.reply);
          } catch (err) {
            resolve('Error: invalid response from backend.');
          }
        });
      });

      req.on('error', () => {
        resolve('Error: cannot connect to backend.');
      });

      req.write(postData);
      req.end();
    });
  }

  async _loadPreviousConversations(webviewView) {
    try {
      const conversations = await this._fetchConversations();
      webviewView.webview.postMessage({ 
        type: 'loadPreviousConversations', 
        conversations: conversations 
      });
    } catch (err) {
      // If error, just continue without previous conversations
      console.error('Error loading previous conversations:', err);
    }
  }

  async _fetchConversations() {
    return new Promise((resolve) => {
      const options = {
        hostname: 'localhost',
        port: 3000,
        path: `/api/conversations/${this._sessionId}`,
        method: 'GET'
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve(json.conversations || []);
          } catch (err) {
            resolve([]);
          }
        });
      });

      req.on('error', () => {
        resolve([]);
      });

      req.end();
    });
  }

  _getHtmlForWebview() {
    const htmlPath = path.join(__dirname, 'webview.html');
    const cssPath = path.join(__dirname, 'webview.css');
    
    const html = fs.readFileSync(htmlPath, 'utf8');
    const css = fs.readFileSync(cssPath, 'utf8');
    
    // Replace the placeholder with actual CSS content
    return html.replace('<link rel="stylesheet" href="{{CSS_PATH}}">', `<style>${css}</style>`);
  }
}

class ChecklistViewProvider {
  static viewType = 'checklistView';

  constructor(extensionUri) {
    this._extensionUri = extensionUri;
  }

  resolveWebviewView(webviewView) {
    webviewView.webview.options = {
      enableScripts: true
    };

    webviewView.webview.html = this._getHtmlForWebview();
    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.type === 'loadRequirements') {
        const requirements = await this._getRequirements();
        webviewView.webview.postMessage({ type: 'requirementsLoaded', requirements });
      } else if (message.type === 'updateCompliance') {
        // Handle compliance status updates if needed
        // Could send to backend to save state
      }
    });
  }

  async _getRequirements() {
    return new Promise((resolve) => {
      const options = {
        hostname: 'localhost',
        port: 3000,
        path: '/api/hipaa-requirements',
        method: 'GET'
      };

      const req = http.request(options, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve(json.requirements || []);
          } catch (err) {
            resolve([]);
          }
        });
      });

      req.on('error', () => {
        resolve([]);
      });

      req.end();
    });
  }

  _getHtmlForWebview() {
    const htmlPath = path.join(__dirname, 'checklist.html');
    const cssPath = path.join(__dirname, 'checklist.css');
    
    const html = fs.readFileSync(htmlPath, 'utf8');
    const css = fs.readFileSync(cssPath, 'utf8');
    
    return html.replace('<link rel="stylesheet" href="{{CSS_PATH}}">', `<style>${css}</style>`);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
