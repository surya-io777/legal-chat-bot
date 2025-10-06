import React, { useState, useRef, useEffect } from 'react';
import {
  Box, TextField, Button, Typography, Paper, Collapse,
  FormControl, InputLabel, Select, MenuItem, IconButton, Chip
} from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import CloseIcon from '@mui/icons-material/Close';
import MessageBubble from './MessageBubble';

function ChatInterface({ messages, onSendMessage, models }) {
  const [inputMessage, setInputMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState('gemini-pro');
  const [userInstructions, setUserInstructions] = useState('');
  const [showInstructions, setShowInstructions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [abortController, setAbortController] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const isNearBottom = () => {
    const container = messagesContainerRef.current;
    if (!container) return true;
    const threshold = 100;
    return container.scrollTop + container.clientHeight >= container.scrollHeight - threshold;
  };

  const handleScroll = () => {
    setShouldAutoScroll(isNearBottom());
  };

  useEffect(() => {
    if (shouldAutoScroll) {
      scrollToBottom();
    }
  }, [messages, shouldAutoScroll]);

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    const newFiles = files.map(file => ({
      file,
      name: file.name,
      size: (file.size / 1024 / 1024).toFixed(2) + ' MB'
    }));
    setUploadedFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSendMessage = async () => {
    if ((!inputMessage.trim() && uploadedFiles.length === 0) || loading) return;
    
    setShouldAutoScroll(true);
    setLoading(true);
    
    // Create abort controller for cancellation
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      // Set loading status based on content
      if (uploadedFiles.length > 0) {
        setLoadingStatus('🔍 Analyzing uploaded files...');
      } else if (inputMessage.toLowerCase().includes('pdf') || inputMessage.toLowerCase().includes('document')) {
        setLoadingStatus('📄 Generating document...');
      } else if (inputMessage.toLowerCase().includes('table')) {
        setLoadingStatus('📊 Creating table...');
      } else {
        setLoadingStatus('🤖 Generating response...');
      }
      
      // Create message with file context
      let messageWithFiles = inputMessage;
      if (uploadedFiles.length > 0) {
        const fileNames = uploadedFiles.map(f => f.name).join(', ');
        messageWithFiles += `\n\nAttached files: ${fileNames}`;
      }
      
      const result = await onSendMessage(messageWithFiles, selectedModel, userInstructions, uploadedFiles, controller.signal);
      if (result.success) {
        setInputMessage('');
        setUploadedFiles([]);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Request was cancelled');
      } else {
        console.error('Error sending message:', error);
      }
    } finally {
      setLoading(false);
      setLoadingStatus('');
      setAbortController(null);
    }
  };
  
  const handleStopGeneration = () => {
    if (abortController) {
      abortController.abort();
      setLoading(false);
      setLoadingStatus('');
      setAbortController(null);
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
            <Typography variant="body2" sx={{ color: 'primary.main', fontWeight: 'bold' }}>
              Gemini 2.5 Pro (Multimodal)
            </Typography>
            <IconButton 
              onClick={() => setShowInstructions(!showInstructions)}
              color={showInstructions ? 'primary' : 'default'}
            >
              <SettingsIcon />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Messages Area - Independent Scroll Container */}
      <Box 
        sx={{ 
          flex: 1, 
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative'
        }}
      >
        <Box 
          ref={messagesContainerRef}
          onScroll={handleScroll}
          sx={{ 
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            p: 1,
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            '&::-webkit-scrollbar': {
              width: '8px'
            },
            '&::-webkit-scrollbar-track': {
              background: '#f5f5f5',
              borderRadius: '4px'
            },
            '&::-webkit-scrollbar-thumb': {
              background: '#1976d2',
              borderRadius: '4px',
              '&:hover': {
                background: '#1565c0'
              }
            }
          }}
        >
          {messages.length === 0 ? (
            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Typography variant="h6" color="text.secondary">
                Welcome to Legal Chat Bot
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Ask legal questions or request document generation
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Chip label="Try: 'Analyze this PDF document'" variant="outlined" sx={{ m: 0.5 }} />
                <Chip label="Try: 'Generate a custody agreement as PDF'" variant="outlined" sx={{ m: 0.5 }} />
                <Chip label="Try: 'Create a table of filing requirements'" variant="outlined" sx={{ m: 0.5 }} />
                <Chip label="Try: 'Read this handwritten document'" variant="outlined" sx={{ m: 0.5 }} />
              </Box>
            </Box>
          ) : (
            messages.map((msg, index) => (
              <MessageBubble key={index} message={msg} />
            ))
          )}
          
          {/* Loading indicator appears after user message */}
          {loading && (
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-start' }}>
              <Box sx={{ 
                p: 3, 
                maxWidth: '70%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 3,
                boxShadow: '0 8px 32px rgba(102, 126, 234, 0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: '-100%',
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
                  animation: 'shimmer 2s infinite',
                  '@keyframes shimmer': {
                    '0%': { left: '-100%' },
                    '100%': { left: '100%' }
                  }
                }
              }}>
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  gap: 1,
                  zIndex: 1
                }}>
                  <Box 
                    sx={{ 
                      width: 6, 
                      height: 24, 
                      bgcolor: 'rgba(255,255,255,0.9)',
                      borderRadius: 1,
                      animation: 'wave1 1.2s infinite ease-in-out',
                      '@keyframes wave1': {
                        '0%, 40%, 100%': { transform: 'scaleY(0.4)' },
                        '20%': { transform: 'scaleY(1.0)' }
                      }
                    }} 
                  />
                  <Box 
                    sx={{ 
                      width: 6, 
                      height: 24, 
                      bgcolor: 'rgba(255,255,255,0.8)',
                      borderRadius: 1,
                      animation: 'wave2 1.2s infinite ease-in-out',
                      animationDelay: '-1.1s',
                      '@keyframes wave2': {
                        '0%, 40%, 100%': { transform: 'scaleY(0.4)' },
                        '20%': { transform: 'scaleY(1.0)' }
                      }
                    }} 
                  />
                  <Box 
                    sx={{ 
                      width: 6, 
                      height: 24, 
                      bgcolor: 'rgba(255,255,255,0.9)',
                      borderRadius: 1,
                      animation: 'wave3 1.2s infinite ease-in-out',
                      animationDelay: '-1.0s',
                      '@keyframes wave3': {
                        '0%, 40%, 100%': { transform: 'scaleY(0.4)' },
                        '20%': { transform: 'scaleY(1.0)' }
                      }
                    }} 
                  />
                  <Box 
                    sx={{ 
                      width: 6, 
                      height: 24, 
                      bgcolor: 'rgba(255,255,255,0.7)',
                      borderRadius: 1,
                      animation: 'wave4 1.2s infinite ease-in-out',
                      animationDelay: '-0.9s',
                      '@keyframes wave4': {
                        '0%, 40%, 100%': { transform: 'scaleY(0.4)' },
                        '20%': { transform: 'scaleY(1.0)' }
                      }
                    }} 
                  />
                  <Box 
                    sx={{ 
                      width: 6, 
                      height: 24, 
                      bgcolor: 'rgba(255,255,255,0.8)',
                      borderRadius: 1,
                      animation: 'wave5 1.2s infinite ease-in-out',
                      animationDelay: '-0.8s',
                      '@keyframes wave5': {
                        '0%, 40%, 100%': { transform: 'scaleY(0.4)' },
                        '20%': { transform: 'scaleY(1.0)' }
                      }
                    }} 
                  />
                </Box>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: 'white',
                    fontWeight: 500,
                    textShadow: '0 1px 2px rgba(0,0,0,0.1)',
                    zIndex: 1
                  }}
                >
                  {loadingStatus}
                </Typography>
              </Box>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>
      </Box>

      {/* Input Area - Fixed Position */}
      <Box 
        sx={{ 
          p: 2, 
          borderTop: 1, 
          borderColor: 'divider', 
          bgcolor: 'background.paper',
          position: 'sticky',
          bottom: 0,
          zIndex: 1
        }}
      >
        
        {/* File Upload Area */}
        {uploadedFiles.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Attached Files:
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {uploadedFiles.map((fileObj, index) => (
                <Chip
                  key={index}
                  label={`${fileObj.name} (${fileObj.size})`}
                  onDelete={() => removeFile(index)}
                  deleteIcon={<CloseIcon />}
                  variant="outlined"
                  size="small"
                />
              ))}
            </Box>
          </Box>
        )}
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            multiple
            accept=".pdf,.doc,.docx,.txt"
            style={{ display: 'none' }}
          />
          
          <IconButton
            onClick={() => fileInputRef.current?.click()}
            color="primary"
            disabled={loading}
          >
            <AttachFileIcon />
          </IconButton>
          
          <TextField
            fullWidth
            multiline
            maxRows={4}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask legal questions, upload PDFs/images, request documents or tables - Gemini 2.5 Pro with multimodal capabilities"
            variant="outlined"
            disabled={loading}
          />
          
          {loading ? (
            <Button 
              onClick={handleStopGeneration}
              variant="outlined"
              sx={{ 
                minWidth: 'auto', 
                px: 2,
                color: 'grey.500',
                borderColor: 'grey.300',
                '&:hover': {
                  borderColor: 'grey.400',
                  bgcolor: 'grey.50'
                }
              }}
            >
              ⏹️
            </Button>
          ) : (
            <Button 
              onClick={handleSendMessage} 
              variant="contained"
              disabled={!inputMessage.trim() && uploadedFiles.length === 0}
              sx={{ minWidth: 'auto', px: 2 }}
            >
              <SendIcon />
            </Button>
          )}
        </Box>
        

        
        {userInstructions && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Custom instructions active
          </Typography>
        )}
        
        {uploadedFiles.length > 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {uploadedFiles.length} file(s) attached
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export default ChatInterface;