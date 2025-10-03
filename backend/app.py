from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import verify_token, create_user, authenticate_user
from chat import ChatService
import os

app = Flask(__name__)
CORS(app)

chat_service = ChatService()

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    return create_user(data['email'], data['password'], data['name'])

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    data = request.json
    return authenticate_user(data['email'], data['password'])

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available models"""
    return jsonify({'models': chat_service.get_available_models()})

@app.route('/api/chat', methods=['POST'])
def chat():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = verify_token(token)
    if not user_data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    return chat_service.send_message(
        user_data['sub'], 
        data['message'], 
        data.get('session_id'),
        data.get('model', 'claude-sonnet-4'),
        data.get('user_instructions', "")
    )

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = verify_token(token)
    if not user_data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    return chat_service.get_user_sessions(user_data['sub'])

@app.route('/api/chat/session/<session_id>', methods=['GET'])
def get_session_messages(session_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    user_data = verify_token(token)
    if not user_data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    return chat_service.get_session_messages(user_data['sub'], session_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)