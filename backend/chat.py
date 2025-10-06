import boto3
import json
from datetime import datetime
import uuid
from utils import generate_pdf, generate_table, generate_legal_document
import os

class ChatService:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        try:
            self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        except Exception as e:
            print(f"Warning: bedrock-agent-runtime not available: {e}")
            self.bedrock_agent = None
        self.table = self.dynamodb.Table('Legal-bot-chat-history')
        self.knowledge_base_id = 'GL3HPG5NUR'
        
        # Load your custom prompt
        self.system_prompt = self.load_prompt_file()
        
        # Available models
        self.models = {
            'claude-sonnet-4': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'nova-pro': 'amazon.nova-pro-v1:0'
        }
    
    def load_prompt_file(self):
        """Load your custom prompt.txt file"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error loading prompt.txt: {e}")
            return "You are Legal Chat Bot, a professional legal assistant."
    
    def retrieve_from_kb(self, query):
        """Retrieve relevant documents from Knowledge Base"""
        if not self.bedrock_agent:
            print("Bedrock agent not available, using fallback context")
            return f"Legal context for: {query}", []
            
        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={'text': query}
            )
            
            context = ""
            sources = []
            
            for result in response['retrievalResults']:
                content = result['content']['text']
                source = result['location']['s3Location']['uri']
                context += f"{content}\n\n"
                sources.append(source)
            
            return context, sources
            
        except Exception as e:
            print(f"KB retrieval error: {e}")
            return f"Legal context for: {query}", []
    
    def detect_document_request(self, message):
        """Detect if user wants document generation"""
        doc_keywords = [
            'generate document', 'create document', 'prepare document',
            'draft agreement', 'create agreement', 'prepare petition',
            'generate pdf', 'create pdf', 'make document',
            'prepare contract', 'draft contract', 'create legal document',
            'draft', 'prepare', 'create petition', 'generate agreement',
            'make agreement', 'write document', 'compose document'
        ]
        
        table_keywords = [
            'create table', 'generate table', 'make table',
            'create chart', 'generate chart', 'show table',
            'table format', 'tabular', 'spreadsheet'
        ]
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in doc_keywords):
            return 'document'
        elif any(keyword in message_lower for keyword in table_keywords):
            return 'table'
        else:
            return 'chat'
    
    def generate_response(self, user_query, context, model_name='claude-sonnet-4', request_type='chat', user_instructions=""):
        """Generate response using selected model and your prompt"""
        
        model_id = self.models.get(model_name, self.models['claude-sonnet-4'])
        
        # Build enhanced prompt based on request type
        if request_type == 'document':
            combined_prompt = f"""{self.system_prompt}

ADDITIONAL USER INSTRUCTIONS:
{user_instructions}

Knowledge Base Context:
{context}

User Request: {user_query}

IMPORTANT: The user is requesting document generation. You MUST:
1. Create a comprehensive legal document based on the request
2. Use proper legal formatting and structure
3. Include all necessary clauses and sections
4. Make it professional and legally sound
5. Use the knowledge base context to inform the document content

Generate a complete, detailed legal document:"""
        elif request_type == 'table':
            combined_prompt = f"""{self.system_prompt}

Knowledge Base Context:
{context}

User Request: {user_query}

IMPORTANT: The user is requesting table/chart generation. You MUST:
1. Create structured data in table format
2. Use | symbols to separate columns
3. Include headers and organized rows
4. Make the data clear and useful

Generate a well-structured table:"""
        else:
            # Regular chat response
            if user_instructions.strip():
                combined_prompt = f"""{self.system_prompt}

ADDITIONAL USER INSTRUCTIONS:
{user_instructions}

Knowledge Base Context:
{context}

User Request: {user_query}

Follow both the system protocols and the user's additional instructions above.

Response:"""
            else:
                combined_prompt = f"""{self.system_prompt}

Knowledge Base Context:
{context}

User Request: {user_query}

Response:"""
        
        try:
            if model_name == 'claude-sonnet-4':
                response = self.bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4000,
                        "messages": [
                            {
                                "role": "user",
                                "content": combined_prompt
                            }
                        ]
                    })
                )
                result = json.loads(response['body'].read())
                return result['content'][0]['text']
                
            elif model_name == 'nova-pro':
                response = self.bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps({
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"text": combined_prompt}]
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": 4000,
                            "temperature": 0.3
                        }
                    })
                )
                result = json.loads(response['body'].read())
                return result['output']['message']['content'][0]['text']
                
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def send_message(self, user_id, message, session_id=None, model_name='claude-sonnet-4', user_instructions="", uploaded_files=[]):
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        timestamp = datetime.now().isoformat()
        
        # Detect request type
        request_type = self.detect_document_request(message)
        
        # Save user message
        self.table.put_item(
            Item={
                'user_id': user_id,
                'message_timestamp': timestamp,
                'session_id': session_id,
                'message_type': 'user',
                'message_content': message,
                'session_title': message[:50] + '...' if len(message) > 50 else message,
                'model_used': model_name,
                'request_type': request_type,
                'user_instructions': user_instructions
            }
        )
        
        try:
            # Process uploaded files
            file_context = ""
            if uploaded_files:
                file_context = self.process_uploaded_files(uploaded_files)
                message += f"\n\nFile Analysis:\n{file_context}"
            
            # Retrieve from Knowledge Base
            kb_context, sources = self.retrieve_from_kb(message)
            
            # Generate response with your prompt
            bot_response = self.generate_response(message, kb_context, model_name, request_type, user_instructions)
            
            # Save assistant response
            assistant_timestamp = datetime.now().isoformat()
            self.table.put_item(
                Item={
                    'user_id': user_id,
                    'message_timestamp': assistant_timestamp,
                    'session_id': session_id,
                    'message_type': 'assistant',
                    'message_content': bot_response,
                    'session_title': message[:50] + '...' if len(message) > 50 else message,
                    'model_used': model_name,
                    'sources': sources,
                    'request_type': request_type
                }
            )
            
            # Generate output files based on request type
            output_files = []
            
            if request_type == 'document':
                pdf_url = generate_legal_document(bot_response, session_id, message)
                output_files.append({
                    'type': 'pdf', 
                    'url': pdf_url,
                    'title': f"Legal Document - {message[:30]}..."
                })
            
            elif request_type == 'table':
                table_url = generate_table(bot_response, session_id)
                output_files.append({
                    'type': 'table', 
                    'url': table_url,
                    'title': f"Table - {message[:30]}..."
                })
            
            return {
                'success': True,
                'response': bot_response,
                'session_id': session_id,
                'model_used': model_name,
                'sources': sources,
                'request_type': request_type,
                'output_files': output_files
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            # Clean up temporary files
            for file_info in uploaded_files:
                try:
                    if os.path.exists(file_info['path']):
                        os.remove(file_info['path'])
                except:
                    pass
    
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and extract content"""
        file_contents = []
        
        for file_info in uploaded_files:
            filename = file_info['filename']
            filepath = file_info['path']
            
            try:
                if filename.lower().endswith('.pdf'):
                    # Extract text from PDF
                    from pypdf import PdfReader
                    reader = PdfReader(filepath)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    file_contents.append(f"File: {filename}\nContent: {text[:2000]}...")  # Limit content
                    
                elif filename.lower().endswith(('.txt', '.doc', '.docx')):
                    # Read text files
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    file_contents.append(f"File: {filename}\nContent: {content[:2000]}...")  # Limit content
                    
                else:
                    file_contents.append(f"File: {filename} (unsupported format)")
                    
            except Exception as e:
                file_contents.append(f"File: {filename} (error reading: {str(e)})")
        
        return "\n\n".join(file_contents)
    
    def get_available_models(self):
        return [
            {'id': 'claude-sonnet-4', 'name': 'Claude 3.5 Sonnet v2'},
            {'id': 'nova-pro', 'name': 'Amazon Nova Pro'}
        ]
    
    def get_user_sessions(self, user_id):
        try:
            response = self.table.query(
                KeyConditionExpression='user_id = :uid',
                ExpressionAttributeValues={':uid': user_id},
                ScanIndexForward=False
            )
            
            sessions = {}
            for item in response['Items']:
                sid = item['session_id']
                if sid not in sessions:
                    sessions[sid] = {
                        'session_id': sid,
                        'title': item['session_title'],
                        'last_message': item['message_content'][:100],
                        'timestamp': item['message_timestamp'],
                        'model_used': item.get('model_used', 'claude-sonnet-4'),
                        'request_type': item.get('request_type', 'chat')
                    }
            
            return {'success': True, 'sessions': list(sessions.values())}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_session_messages(self, user_id, session_id):
        try:
            response = self.table.query(
                KeyConditionExpression='user_id = :uid',
                FilterExpression='session_id = :sid',
                ExpressionAttributeValues={
                    ':uid': user_id,
                    ':sid': session_id
                },
                ScanIndexForward=True
            )
            
            return {'success': True, 'messages': response['Items']}
        except Exception as e:
            return {'success': False, 'error': str(e)}