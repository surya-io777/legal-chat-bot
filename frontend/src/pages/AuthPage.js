import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Alert } from '@mui/material';
import { authService } from '../services/authService';

function AuthPage({ setAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      let result;
      if (isLogin) {
        result = await authService.signin(formData.email, formData.password);
      } else {
        result = await authService.signup(formData.email, formData.password, formData.name);
      }
      
      if (result.success) {
        if (isLogin) {
          localStorage.setItem('access_token', result.access_token);
          setAuth(true);
        } else {
          alert('Account created! Please sign in.');
          setIsLogin(true);
          setFormData({ email: '', password: '', name: '' });
        }
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Paper sx={{ p: 4 }}>
          <Typography variant="h4" align="center" gutterBottom>
            Legal Chat Bot
          </Typography>
          <Typography variant="h6" align="center" gutterBottom color="text.secondary">
            {isLogin ? 'Sign In' : 'Create Account'}
          </Typography>
          
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              margin="normal"
              required
            />
            
            {!isLogin && (
              <TextField
                fullWidth
                label="Full Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                margin="normal"
                required
              />
            )}
            
            <TextField
              fullWidth
              label="Password"
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              margin="normal"
              required
            />
            
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
            </Button>
            
            <Button
              fullWidth
              onClick={() => {
                setIsLogin(!isLogin);
                setError('');
                setFormData({ email: '', password: '', name: '' });
              }}
            >
              {isLogin ? 'Need an account? Sign Up' : 'Have an account? Sign In'}
            </Button>
          </form>
        </Paper>
      </Box>
    </Container>
  );
}

export default AuthPage;