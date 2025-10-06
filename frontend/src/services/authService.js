import axios from 'axios';

const API_BASE = 'http://44.204.88.183:5000/api';

export const authService = {
  async signin(email, password) {
    const response = await axios.post(`${API_BASE}/auth/signin`, {
      email, password
    });
    return response.data;
  },

  async signup(email, password, name) {
    const response = await axios.post(`${API_BASE}/auth/signup`, {
      email, password, name
    });
    return response.data;
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