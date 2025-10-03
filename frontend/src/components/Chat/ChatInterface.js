import React, { useState, useRef, useEffect } from 'react';
import {
  Box, TextField, Button, Typography, Paper, Collapse,
  FormControl, InputLabel, Select, MenuItem, IconButton, Chip
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import SendIcon from '@mui/icons-material/Send';
import MessageBubble from './MessageBubble';

function ChatInterface({ messages, onSendMessage, models }) {
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4');
  const [userInstructions, setUserInstructions] = useState('');
  const [showInstructions, setShowInstructions] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return;
    
    setLoading(true);
    try {
      const result = await onSendMessage(inputMessage, selectedModel, userInstructions);
      if (result.success) {
        setInputMessage('');
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      
      {/* Instructions Panel */}
      <Collapse in={showInstructions}>
        <Paper sx={{ p: 2, m: 1, bgcolor: 'grey.50' }}>
          <Typography variant="subtitle1" gutterBottom>
            Custom Instructions
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={userInstructions}
            onChange={(e) => setUserInstructions(e.target.value)}
            placeholder="Add custom instructions (e.g., 'Focus on Virginia law', 'Use simple language', 'Include practical examples')"
            variant="outlined"
            size="small"
          />
        </Paper>
      </Collapse>

      {/* Chat Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Chat Assistant
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Model</InputLabel>
              <Select
                value={selectedModel}
                label="Model"
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {models.map((model) => (
                  <MenuItem key={model.id} value={model.id}>
                    {model.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <IconButton 
              onClick={() => setShowInstructions(!showInstructions)}
              color={showInstructions ? 'primary' : 'default'}
            >
              <SettingsIcon />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Messages Area */}
      <Box sx={{ flex: 1, overflow: 'auto', p: 1 }}>
        {messages.length === 0 ? (
          <Box sx={{ textAlign: 'center', mt: 4 }}>
            <Typography variant="h6" color="text.secondary">
              Welcome to Legal Chat Bot
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Ask legal questions or request document generation
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Chip label="Try: 'What are custody requirements?'" variant="outlined" sx={{ m: 0.5 }} />
              <Chip label="Try: 'Generate a custody agreement'" variant="outlined" sx={{ m: 0.5 }} />
              <Chip label="Try: 'Create a table of filing requirements'" variant="outlined" sx={{ m: 0.5 }} />
            </Box>
          </Box>
        ) : (
          messages.map((msg, index) => (
            <MessageBubble key={index} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a legal question or request document generation..."
            variant="outlined"
            disabled={loading}
          />
          <Button 
            onClick={handleSendMessage} 
            variant="contained"
            disabled={loading || !inputMessage.trim()}
            sx={{ minWidth: 'auto', px: 2 }}
          >
            <SendIcon />
          </Button>
        </Box>
        {userInstructions && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Custom instructions active
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export default ChatInterface;