import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

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
  }
};