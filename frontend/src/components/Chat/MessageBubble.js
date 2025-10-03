import React from 'react';
import { Box, Paper, Typography, Chip, Button } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';

function MessageBubble({ message }) {
  const isUser = message.message_type === 'user';
  
  const handleDownload = (file) => {
    window.open(file.url, '_blank');
  };

  return (
    <Box sx={{ mb: 2, display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <Paper 
        sx={{ 
          p: 2, 
          maxWidth: '70%',
          bgcolor: isUser ? 'primary.main' : 'grey.100',
          color: isUser ? 'white' : 'text.primary'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          {isUser ? <PersonIcon sx={{ mr: 1, fontSize: 20 }} /> : <SmartToyIcon sx={{ mr: 1, fontSize: 20 }} />}
          <Typography variant="caption">
            {isUser ? 'You' : 'Legal Chat Bot'}
          </Typography>
          {message.model_used && !isUser && (
            <Chip 
              label={message.model_used} 
              size="small" 
              sx={{ ml: 1, height: 20 }} 
            />
          )}
        </Box>
        
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.message_content}
        </Typography>
        
        {message.sources && message.sources.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
              Sources:
            </Typography>
            {message.sources.map((source, index) => (
              <Typography key={index} variant="caption" sx={{ display: 'block', ml: 1 }}>
                • {source.split('/').pop()}
              </Typography>
            ))}
          </Box>
        )}
        
        {message.output_files && message.output_files.length > 0 && (
          <Box sx={{ mt: 2 }}>
            {message.output_files.map((file, index) => (
              <Button
                key={index}
                variant="outlined"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => handleDownload(file)}
                sx={{ mr: 1, mb: 1 }}
              >
                {file.title || `Download ${file.type.toUpperCase()}`}
              </Button>
            ))}
          </Box>
        )}
        
        <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
          {new Date(message.message_timestamp).toLocaleTimeString()}
        </Typography>
      </Paper>
    </Box>
  );
}

export default MessageBubble;