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
    
    // Clean content and format for better readability
    let cleanContent = content
      .replace(/\*\*/g, '') // Remove ** formatting
      .replace(/###/g, '') // Remove ### headers
      .replace(/##/g, '') // Remove ## headers
      .replace(/#/g, ''); // Remove # headers
    
    // Split into paragraphs and format
    const paragraphs = cleanContent.split('\n\n');
    const formattedContent = [];
    
    paragraphs.forEach((paragraph, index) => {
      const trimmedParagraph = paragraph.trim();
      
      if (!trimmedParagraph) return;
      
      // Check if it's a numbered list item
      if (/^\d+\./.test(trimmedParagraph)) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mb: 1,
            pl: 2,
            fontWeight: 'bold'
          }}>
            {trimmedParagraph}
          </Typography>
        );
      }
      // Check if it's a bullet point
      else if (trimmedParagraph.startsWith('•') || trimmedParagraph.startsWith('-')) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mb: 0.5,
            pl: 2
          }}>
            {trimmedParagraph}
          </Typography>
        );
      }
      // Check if it's a title (all caps or contains AGREEMENT, etc.)
      else if (trimmedParagraph === trimmedParagraph.toUpperCase() || 
               trimmedParagraph.includes('AGREEMENT') || 
               trimmedParagraph.includes('RECITALS')) {
        formattedContent.push(
          <Typography key={index} variant="h6" sx={{ 
            fontWeight: 'bold', 
            mt: 2, 
            mb: 1,
            textAlign: 'center'
          }}>
            {trimmedParagraph}
          </Typography>
        );
      }
      // Regular paragraph
      else {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mb: 1,
            lineHeight: 1.6,
            textAlign: 'justify'
          }}>
            {trimmedParagraph}
          </Typography>
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
      .replace(/#/g, '')
      .replace(/SRIS Juris Support states:/g, '');
    
    const blob = new Blob([cleanContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal_document_${new Date(timestamp).getTime()}.pdf`;
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
        
        {/* Only show download for document generation requests */}
        {!isUser && message.message_content && message.message_content.length > 1000 && (
          message.message_content.toLowerCase().includes('agreement') ||
          message.message_content.toLowerCase().includes('contract') ||
          message.message_content.toLowerCase().includes('petition') ||
          message.message_content.toLowerCase().includes('document')
        ) && (
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