import React from 'react';
import { 
  Box, List, ListItem, ListItemText, Typography, Button, 
  Divider, Paper, Chip 
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ChatIcon from '@mui/icons-material/Chat';

function Sidebar({ sessions, onSessionSelect, currentSession, onNewChat }) {
  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'background.paper' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Button
          fullWidth
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onNewChat}
        >
          New Chat
        </Button>
      </Box>
      
      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Typography variant="h6" sx={{ p: 2, pb: 1, borderBottom: 1, borderColor: 'divider' }}>
          Chat History
        </Typography>
        
        <Box sx={{ 
          flex: 1, 
          overflowY: 'auto',
          position: 'relative',
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
        }}>
          <List sx={{ pt: 0 }}>
          {sessions.map((session) => (
            <ListItem
              key={session.session_id}
              button
              selected={currentSession === session.session_id}
              onClick={() => onSessionSelect(session.session_id)}
              sx={{ 
                borderLeft: currentSession === session.session_id ? 3 : 0,
                borderColor: 'primary.main',
                '&:hover': { bgcolor: 'action.hover' }
              }}
            >
              <Box sx={{ width: '100%' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <ChatIcon sx={{ mr: 1, fontSize: 16 }} />
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(session.timestamp)}
                  </Typography>
                </Box>
                
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: currentSession === session.session_id ? 'bold' : 'normal',
                    mb: 0.5
                  }}
                >
                  {session.title}
                </Typography>
                
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {session.last_message}
                </Typography>
                
                <Box sx={{ mt: 1, display: 'flex', gap: 0.5 }}>
                  <Chip 
                    label="Gemini 2.5 Pro" 
                    size="small" 
                    variant="outlined"
                    sx={{ fontSize: '0.7rem', height: 20 }}
                  />
                  {session.request_type && session.request_type !== 'chat' && (
                    <Chip 
                      label={session.request_type} 
                      size="small" 
                      color="secondary"
                      sx={{ fontSize: '0.7rem', height: 20 }}
                    />
                  )}
                </Box>
              </Box>
            </ListItem>
          ))}
          </List>
          
          {sessions.length === 0 && (
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                No chat history yet
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default Sidebar;