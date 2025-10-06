import React, { useState, useEffect } from 'react';
import { Box, Grid, AppBar, Toolbar, Typography, Button } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import Sidebar from '../components/Sidebar/Sidebar';
import ChatInterface from '../components/Chat/ChatInterface';
import { chatService } from '../services/chatService';

function ChatPage({ setAuth }) {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [models, setModels] = useState([]);

  useEffect(() => {
    loadSessions();
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const result = await chatService.getModels();
      setModels(result.models || []);
    } catch (error) {
      console.error('Error loading models:', error);
    }
  };

  const loadSessions = async () => {
    const result = await chatService.getUserSessions();
    if (result.success) {
      setSessions(result.sessions);
    }
  };

  const loadSession = async (sessionId) => {
    const result = await chatService.getSessionMessages(sessionId);
    if (result.success) {
      setMessages(result.messages);
      setCurrentSession(sessionId);
    }
  };

  const sendMessage = async (message, model, userInstructions, files = []) => {
    const result = await chatService.sendMessage(message, currentSession, model, userInstructions, files);
    if (result.success) {
      loadSessions(); // Refresh sessions
      if (currentSession === result.session_id || !currentSession) {
        loadSession(result.session_id); // Refresh current session
        setCurrentSession(result.session_id);
      }
    }
    return result;
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setAuth(false);
  };

  const startNewChat = () => {
    setCurrentSession(null);
    setMessages([]);
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Legal Chat Bot
          </Typography>
          <Button color="inherit" onClick={handleLogout} startIcon={<LogoutIcon />}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>
      
      <Box sx={{ flex: 1, display: 'flex' }}>
        <Grid container sx={{ height: '100%' }}>
          <Grid item xs={3}>
            <Sidebar 
              sessions={sessions}
              onSessionSelect={loadSession}
              currentSession={currentSession}
              onNewChat={startNewChat}
            />
          </Grid>
          <Grid item xs={9}>
            <ChatInterface 
              messages={messages}
              onSendMessage={sendMessage}
              models={models}
            />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
}

export default ChatPage;