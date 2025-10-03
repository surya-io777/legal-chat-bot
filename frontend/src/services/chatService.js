import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

const getAuthHeaders = () => ({
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

export const chatService = {
  async sendMessage(message, sessionId, model = 'claude-sonnet-4', userInstructions = '') {
    const response = await axios.post(`${API_BASE}/chat`, {
      message, 
      session_id: sessionId,
      model,
      user_instructions: userInstructions
    }, getAuthHeaders());
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