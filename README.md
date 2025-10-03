# Legal Chat Bot

AI-powered legal assistant with document generation capabilities.

## Features

- **Authentication**: AWS Cognito user management
- **Chat Interface**: Real-time legal Q&A
- **Model Selection**: Claude Sonnet 4 and Amazon Nova Pro
- **Custom Instructions**: User-specific prompting
- **Document Generation**: PDF and table outputs
- **Knowledge Base**: Integration with legal documents
- **Chat History**: Persistent conversation storage

## Setup Instructions

### Prerequisites

- AWS Account with Bedrock access
- Python 3.8+
- Node.js 16+
- Git

### Backend Setup

1. **Clone Repository**
   ```bash
   git clone <your-repo-url>
   cd legal-chat-bot/backend
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add Your Prompt File**
   ```bash
   # Copy your prompt.txt to backend directory
   cp /path/to/your/prompt.txt ./prompt.txt
   ```

4. **Configure AWS Services**
   - Ensure DynamoDB table `Legal-bot-chat-history` exists
   - Ensure S3 bucket `legal-chat-bot-outputs` exists
   - Ensure Knowledge Base `GL3HPG5NUR` is accessible
   - Configure AWS credentials (IAM role or access keys)

5. **Run Backend**
   ```bash
   python app.py
   ```

### Frontend Setup

1. **Navigate to Frontend**
   ```bash
   cd ../frontend
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **Update API Endpoint**
   - Edit `src/services/authService.js` and `src/services/chatService.js`
   - Change `http://localhost:5000/api` to your EC2 backend URL

4. **Run Frontend**
   ```bash
   npm start
   ```

### Production Deployment

1. **Backend (EC2)**
   ```bash
   # Install PM2
   npm install -g pm2
   
   # Start backend
   pm2 start app.py --name legal-chat-bot-backend --interpreter python3
   
   # Start on boot
   pm2 startup
   pm2 save
   ```

2. **Frontend (Build & Serve)**
   ```bash
   # Build for production
   npm run build
   
   # Serve with PM2
   pm2 serve build 3000 --name legal-chat-bot-frontend
   ```

3. **Nginx Configuration** (Optional)
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location /api {
           proxy_pass http://localhost:5000;
       }
       
       location / {
           proxy_pass http://localhost:3000;
       }
   }
   ```

## Configuration

### Environment Variables

Create `.env` file in backend directory:
```
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_9sajhw6fR
COGNITO_CLIENT_ID=2g81deb4kgrp8tm185hpa25jj
DYNAMODB_TABLE=Legal-bot-chat-history
KNOWLEDGE_BASE_ID=GL3HPG5NUR
S3_BUCKET=legal-chat-bot-outputs
```

### Model Configuration

Update `chat.py` to add more models:
```python
self.models = {
    'claude-sonnet-4': 'arn:aws:bedrock:...',
    'nova-pro': 'amazon.nova-pro-v1:0',
    'your-new-model': 'model-id-here'
}
```

## Usage

1. **Sign Up/Sign In**: Create account or login
2. **Start Chat**: Ask legal questions
3. **Generate Documents**: Use keywords like "generate document", "create agreement"
4. **Custom Instructions**: Add specific requirements in settings
5. **Download Files**: Click download buttons for generated documents

## API Endpoints

- `POST /api/auth/signup` - Create user account
- `POST /api/auth/signin` - User authentication
- `GET /api/models` - Get available AI models
- `POST /api/chat` - Send chat message
- `GET /api/chat/history` - Get user's chat sessions
- `GET /api/chat/session/<id>` - Get specific session messages

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check Cognito User Pool ID and Client ID
   - Verify IAM permissions

2. **Knowledge Base Errors**
   - Confirm Knowledge Base ID is correct
   - Check Bedrock permissions

3. **Model Errors**
   - Verify model ARNs are correct
   - Check Bedrock model access

4. **File Generation Errors**
   - Ensure S3 bucket exists and is accessible
   - Check S3 permissions

### Logs

- Backend logs: Check console output or PM2 logs
- Frontend logs: Check browser developer console
- AWS logs: Check CloudWatch for Bedrock/DynamoDB errors

## Support

For issues and questions, check the troubleshooting section or review AWS service documentation.