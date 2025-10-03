import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import AuthPage from './pages/AuthPage';
import ChatPage from './pages/ChatPage';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route 
            path="/auth" 
            element={!isAuthenticated ? <AuthPage setAuth={setIsAuthenticated} /> : <Navigate to="/chat" />} 
          />
          <Route 
            path="/chat" 
            element={isAuthenticated ? <ChatPage setAuth={setIsAuthenticated} /> : <Navigate to="/auth" />} 
          />
          <Route path="/" element={<Navigate to={isAuthenticated ? "/chat" : "/auth"} />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;