import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

const getAuthHeaders = () => ({
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

export const chatService = {
  async sendMessage(message, sessionId, model = 'gemini-pro', userInstructions = '', files = [], abortSignal) {
    const formData = new FormData();
    formData.append('message', message);
    formData.append('session_id', sessionId || '');
    formData.append('model', model);
    formData.append('user_instructions', userInstructions);
    
    // Add files to form data
    files.forEach((fileObj, index) => {
      formData.append(`file_${index}`, fileObj.file);
    });
    
    const response = await axios.post(`${API_BASE}/chat`, formData, {
      ...getAuthHeaders(),
      headers: {
        ...getAuthHeaders().headers,
        'Content-Type': 'multipart/form-data'
      },
      signal: abortSignal,
      timeout: 120000 // 2 minute timeout
    });
    return response.data;
  },

  async getUserSessions() {
    const response = await axios.get(`${API_BASE}/chat/history`, getAuthHeaders());
    return response.data;
  },

  async getSessionMessages(sessionId) {
    const response = await axios.get(`${API_BASE}/chat/session/${sessionId}`, getAuthHeaders());
    return response.data;
  },

  async getModels() {
    const response = await axios.get(`${API_BASE}/models`, getAuthHeaders());
    return response.data;
  }
};