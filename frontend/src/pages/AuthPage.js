import React, { useState } from 'react';
import { Container, Paper, TextField, Button, Typography, Box, Alert } from '@mui/material';
import { authService } from '../services/authService';

function AuthPage({ setAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [showVerification, setShowVerification] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    code: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      let result;
      
      if (showVerification) {
        result = await authService.verifyEmail(formData.email, formData.code);
        if (result.success) {
          setSuccess('Email verified! You can now sign in.');
          setShowVerification(false);
          setIsLogin(true);
        }
      } else if (showForgotPassword) {
        result = await authService.forgotPassword(formData.email);
        if (result.success) {
          setSuccess('Reset code sent to your email!');
          setShowForgotPassword(false);
          setShowResetPassword(true);
        }
      } else if (showResetPassword) {
        result = await authService.resetPassword(formData.email, formData.code, formData.password);
        if (result.success) {
          setSuccess('Password reset successfully! You can now sign in.');
          setShowResetPassword(false);
          setIsLogin(true);
        }
      } else if (isLogin) {
        result = await authService.signin(formData.email, formData.password);
        if (result.success) {
          localStorage.setItem('access_token', result.access_token);
          setAuth(true);
        }
      } else {
        result = await authService.signup(formData.email, formData.password, formData.name);
        if (result.success) {
          setSuccess('Account created! Please check your email for verification.');
          setShowVerification(true);
          setIsLogin(false);
        }
      }
      
      if (!result.success) {
        setError(result.error);
      }
    } catch (error) {
      console.error('Auth error:', error);
      if (error.response?.data?.error) {
        setError(error.response.data.error);
      } else if (error.message) {
        setError(error.message);
      } else {
        setError('Authentication failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const resetForm = () => {
    setFormData({ email: '', password: '', name: '', code: '' });
    setError('');
    setSuccess('');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8 }}>
        <Paper sx={{ p: 4 }}>
          <Typography variant="h4" align="center" gutterBottom>
            Legal Chat Bot
          </Typography>
          <Typography variant="h6" align="center" gutterBottom color="text.secondary">
            {showVerification ? 'Verify Email' : 
             showForgotPassword ? 'Forgot Password' :
             showResetPassword ? 'Reset Password' :
             isLogin ? 'Sign In' : 'Create Account'}
          </Typography>
          
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
          
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              margin="normal"
              required
              disabled={showVerification || showResetPassword}
            />
            
            {!isLogin && !showVerification && !showForgotPassword && !showResetPassword && (
              <TextField
                fullWidth
                label="Full Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                margin="normal"
                required
              />
            )}
            
            {(showVerification || showResetPassword) && (
              <TextField
                fullWidth
                label="Verification Code"
                value={formData.code}
                onChange={(e) => setFormData({...formData, code: e.target.value})}
                margin="normal"
                required
              />
            )}
            
            {!showForgotPassword && (
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                margin="normal"
                required={!showVerification}
              />
            )}
            
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Please wait...' : 
               showVerification ? 'Verify Email' :
               showForgotPassword ? 'Send Reset Code' :
               showResetPassword ? 'Reset Password' :
               isLogin ? 'Sign In' : 'Create Account'}
            </Button>
            
            {isLogin && !showForgotPassword && !showResetPassword && (
              <Button
                fullWidth
                onClick={() => {
                  setShowForgotPassword(true);
                  setIsLogin(false);
                  resetForm();
                }}
                sx={{ mb: 1 }}
              >
                Forgot Password?
              </Button>
            )}
            
            {showVerification && (
              <Button
                fullWidth
                onClick={async () => {
                  try {
                    const result = await authService.resendVerification(formData.email);
                    if (result.success) {
                      setSuccess('Verification code resent!');
                    } else {
                      setError(result.error);
                    }
                  } catch (error) {
                    setError('Failed to resend code');
                  }
                }}
                sx={{ mb: 1 }}
              >
                Resend Code
              </Button>
            )}
            
            <Button
              fullWidth
              onClick={() => {
                if (showVerification || showForgotPassword || showResetPassword) {
                  setShowVerification(false);
                  setShowForgotPassword(false);
                  setShowResetPassword(false);
                  setIsLogin(true);
                } else {
                  setIsLogin(!isLogin);
                }
                resetForm();
              }}
            >
              {(showVerification || showForgotPassword || showResetPassword) ? 'Back to Sign In' :
               isLogin ? 'Need an account? Sign Up' : 'Have an account? Sign In'}
            </Button>
          </form>
        </Paper>
      </Box>
    </Container>
  );
}

export default AuthPage;