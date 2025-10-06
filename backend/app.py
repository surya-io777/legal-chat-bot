from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from auth import verify_token, create_user, authenticate_user
from chat import ChatService
import os
import tempfile

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
    
    # Handle both JSON and form data
    if request.content_type and 'multipart/form-data' in request.content_type:
        # File upload request
        message = request.form.get('message', '')
        session_id = request.form.get('session_id')
        model = request.form.get('model', 'claude-sonnet-4')
        user_instructions = request.form.get('user_instructions', '')
        
        # Handle uploaded files
        uploaded_files = []
        for key in request.files:
            if key.startswith('file_'):
                file = request.files[key]
                if file and file.filename:
                    # Save file temporarily
                    filename = secure_filename(file.filename)
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    file.save(temp_path)
                    uploaded_files.append({
                        'filename': filename,
                        'path': temp_path
                    })
        
        return chat_service.send_message(
            user_data['sub'], 
            message, 
            session_id,
            model,
            user_instructions,
            uploaded_files
        )
    else:
        # Regular JSON request
        data = request.json
        return chat_service.send_message(
            user_data['sub'], 
            data['message'], 
            data.get('session_id'),
            data.get('model', 'claude-sonnet-4'),
            data.get('user_instructions', ""),
            []
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