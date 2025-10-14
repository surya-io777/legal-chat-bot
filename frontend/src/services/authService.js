import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

export const authService = {
  async signin(email, password) {
    try {
      const response = await axios.post(`${API_BASE}/auth/signin`, {
        email, password
      });
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        throw new Error('Cannot connect to server. Please check if the backend is running on port 5000.');
      }
      throw error;
    }
  },

  async signup(email, password, name) {
    try {
      const response = await axios.post(`${API_BASE}/auth/signup`, {
        email, password, name
      });
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        throw new Error('Cannot connect to server. Please check if the backend is running on port 5000.');
      }
      throw error;
    }
  },

  async verifyEmail(email, code) {
    const response = await axios.post(`${API_BASE}/auth/verify-email`, {
      email, code
    });
    return response.data;
  },

  async resendVerification(email) {
    const response = await axios.post(`${API_BASE}/auth/resend-verification`, {
      email
    });
    return response.data;
  },

  async forgotPassword(email) {
    const response = await axios.post(`${API_BASE}/auth/forgot-password`, {
      email
    });
    return response.data;
  },

  async resetPassword(email, code, password) {
    const response = await axios.post(`${API_BASE}/auth/reset-password`, {
      email, code, password
    });
    return response.data;
  }
};