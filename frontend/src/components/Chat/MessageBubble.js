import React from 'react';
import { Box, Paper, Typography, Chip, Button } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import PersonIcon from '@mui/icons-material/Person';
import SmartToyIcon from '@mui/icons-material/SmartToy';

function MessageBubble({ message }) {
  const isUser = message.message_type === 'user';
  
  const formatLegalDocument = (content, isUserMessage) => {
    if (isUserMessage) {
      return (
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {content}
        </Typography>
      );
    }
    
    // Format legal document structure
    const lines = content.split('\n');
    const formattedContent = [];
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      if (!trimmedLine) {
        formattedContent.push(<Box key={index} sx={{ height: '8px' }} />);
        return;
      }
      
      // Handle markdown-style headers
      if (trimmedLine.startsWith('###')) {
        formattedContent.push(
          <Typography key={index} variant="h4" sx={{ 
            fontWeight: 'bold', 
            mt: 2, 
            mb: 1,
            textAlign: 'center',
            textDecoration: 'underline',
            color: 'primary.main'
          }}>
            {trimmedLine.replace(/^###\s*/, '')}
          </Typography>
        );
      } else if (trimmedLine.startsWith('##')) {
        formattedContent.push(
          <Typography key={index} variant="h5" sx={{ 
            fontWeight: 'bold', 
            mt: 2, 
            mb: 1,
            textAlign: 'center',
            color: 'text.primary'
          }}>
            {trimmedLine.replace(/^##\s*/, '')}
          </Typography>
        );
      } else if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        // Bold headers
        formattedContent.push(
          <Typography key={index} variant="h6" sx={{ 
            fontWeight: 'bold', 
            mt: 1.5, 
            mb: 0.5,
            textAlign: 'center',
            color: 'text.secondary'
          }}>
            {trimmedLine.replace(/\*\*/g, '')}
          </Typography>
        );
      } else {
        // Regular paragraph with bold text support
        const formattedText = trimmedLine.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mb: 0.5,
            textAlign: trimmedLine.includes('AGREEMENT') || trimmedLine.includes('RECITALS') ? 'center' : 'left',
            fontWeight: trimmedLine.includes('WHEREAS') || trimmedLine.includes('NOW THEREFORE') ? 'bold' : 'normal',
            lineHeight: 1.6
          }} dangerouslySetInnerHTML={{ __html: formattedText }} />
        );
      }
    });
    
    return <Box>{formattedContent}</Box>;
  };
  
  const handleDownload = (file) => {
    if (file.content) {
      const blob = file.type === 'pdf' 
        ? new Blob([Uint8Array.from(atob(file.content), c => c.charCodeAt(0))], { type: 'application/pdf' })
        : new Blob([file.content], { type: 'text/csv' });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (file.url) {
      window.open(file.url, '_blank');
    }
  };
  
  const handleAutoDownload = (content, timestamp) => {
    const cleanContent = content
      .replace(/\*\*/g, '')
      .replace(/###/g, '')
      .replace(/##/g, '')
      .replace(/#/g, '');
    
    const blob = new Blob([cleanContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal_document_${new Date(timestamp).getTime()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
        
        {formatLegalDocument(message.message_content, isUser)}
        
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
        
        {/* Auto-generate download for long responses */}
        {!isUser && message.message_content && message.message_content.length > 500 && (
          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              size="small"
              startIcon={<DownloadIcon />}
              onClick={() => handleAutoDownload(message.message_content, message.message_timestamp)}
              sx={{ 
                mr: 1, 
                mb: 1,
                bgcolor: 'success.main',
                '&:hover': {
                  bgcolor: 'success.dark'
                }
              }}
            >
              Download as PDF
            </Button>
          </Box>
        )}
        
        {message.output_files && message.output_files.length > 0 && (
          <Box sx={{ mt: 2 }}>
            {message.output_files.map((file, index) => (
              <Button
                key={index}
                variant="contained"
                size="small"
                startIcon={<DownloadIcon />}
                onClick={() => handleDownload(file)}
                sx={{ 
                  mr: 1, 
                  mb: 1,
                  bgcolor: 'success.main',
                  '&:hover': {
                    bgcolor: 'success.dark'
                  }
                }}
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