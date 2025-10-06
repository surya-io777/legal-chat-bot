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
    
    // Process content line by line for better structure
    const lines = content.split('\n');
    const formattedContent = [];
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      if (!trimmedLine) {
        formattedContent.push(<Box key={index} sx={{ height: '8px' }} />);
        return;
      }
      
      // Main document titles (all caps, centered, bold)
      if (trimmedLine === trimmedLine.toUpperCase() && 
          (trimmedLine.includes('AGREEMENT') || 
           trimmedLine.includes('CONTRACT') || 
           trimmedLine.includes('PETITION') ||
           trimmedLine.includes('SEPARATION') ||
           trimmedLine.includes('RECITALS'))) {
        formattedContent.push(
          <Typography key={index} variant="h5" sx={{ 
            fontWeight: 'bold', 
            mt: 3, 
            mb: 2,
            textAlign: 'center',
            textDecoration: 'underline'
          }}>
            {trimmedLine}
          </Typography>
        );
      }
      // Section headers (WHEREAS, NOW THEREFORE, etc.)
      else if (trimmedLine.startsWith('WHEREAS') || 
               trimmedLine.startsWith('NOW THEREFORE') ||
               trimmedLine.startsWith('IT IS AGREED') ||
               trimmedLine.includes('WITNESSETH')) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            fontWeight: 'bold',
            mt: 2,
            mb: 1,
            textIndent: '20px'
          }}>
            {trimmedLine}
          </Typography>
        );
      }
      // Numbered clauses (1., 2., etc.)
      else if (/^\d+\./.test(trimmedLine)) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            fontWeight: 'bold',
            mt: 1.5,
            mb: 0.5,
            pl: 1
          }}>
            {trimmedLine}
          </Typography>
        );
      }
      // Sub-clauses (a., b., etc.)
      else if (/^[a-z]\)/.test(trimmedLine) || /^\([a-z]\)/.test(trimmedLine)) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mt: 0.5,
            mb: 0.5,
            pl: 3,
            fontStyle: 'italic'
          }}>
            {trimmedLine}
          </Typography>
        );
      }
      // Names and important terms (in quotes or all caps)
      else if (trimmedLine.includes('"') || 
               (trimmedLine === trimmedLine.toUpperCase() && trimmedLine.length < 50)) {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            fontWeight: 'bold',
            mb: 0.5,
            textAlign: 'center'
          }}>
            {trimmedLine}
          </Typography>
        );
      }
      // Regular paragraphs
      else {
        formattedContent.push(
          <Typography key={index} variant="body1" sx={{ 
            mb: 0.8,
            lineHeight: 1.6,
            textAlign: 'justify',
            textIndent: '20px'
          }}>
            {trimmedLine}
          </Typography>
        );
      }
    });
    
    return <Box sx={{ p: 1 }}>{formattedContent}</Box>;
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
    // Clean content
    const cleanContent = content
      .replace(/\*\*/g, '')
      .replace(/###/g, '')
      .replace(/##/g, '')
      .replace(/#/g, '')
      .replace(/SRIS Juris Support states:/g, '')
      .trim();
    
    // Generate proper PDF using jsPDF CDN
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
    script.onload = () => {
      try {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        
        // Add title
        doc.setFontSize(16);
        doc.text('Legal Document', 20, 20);
        
        // Add content
        doc.setFontSize(12);
        const lines = doc.splitTextToSize(cleanContent, 170);
        let yPosition = 40;
        
        lines.forEach((line) => {
          if (yPosition > 280) {
            doc.addPage();
            yPosition = 20;
          }
          doc.text(line, 20, yPosition);
          yPosition += 7;
        });
        
        doc.save(`legal_document_${new Date(timestamp).getTime()}.pdf`);
      } catch (error) {
        // Fallback to text file
        const blob = new Blob([cleanContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `legal_document_${new Date(timestamp).getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    };
    document.head.appendChild(script);
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
        

        
        {/* Show download for long responses or when PDF keywords detected */}
        {!isUser && (message.output_files?.length > 0 || 
                    message.message_content?.length > 1000 || 
                    message.message_content?.toLowerCase().includes('pdf') ||
                    message.request_type === 'document' ||
                    message.request_type === 'fill_form') && (
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
              {message.request_type === 'fill_form' ? 'Download Filled Form' : 'Download PDF'}
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