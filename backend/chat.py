import boto3
import json
from datetime import datetime
import uuid
from utils import generate_pdf, generate_table, generate_legal_document
import os
import google.generativeai as genai

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
        
        # Configure Gemini
        genai.configure(api_key="AIzaSyCEKP2j4eHv1LLKvKm6GACh6s7-K67YYR8")
        
        # Available models
        self.models = {
            'claude-4-sonnet': 'arn:aws:bedrock:us-east-1:293354969601:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0',
            'claude-3-5-sonnet': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'nova-pro': 'amazon.nova-pro-v1:0',
            'gemini-pro': 'gemini-2.5-pro'
        }
    
    def load_prompt_file(self):
        """Load your custom prompt.txt file"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
            with open(prompt_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"✅ PROMPT LOADED: {len(content)} characters from {prompt_path}")
                print(f"✅ PROMPT PREVIEW: {content[:200]}...")
                return content
        except Exception as e:
            print(f"❌ ERROR loading prompt.txt: {e}")
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
        
        model_id = self.models.get(model_name, self.models['claude-4-sonnet'])
        
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
            # Regular chat response - ENFORCE SRIS FORMAT
            if user_instructions.strip():
                combined_prompt = f"""{self.system_prompt}

ADDITIONAL USER INSTRUCTIONS:
{user_instructions}

Knowledge Base Context:
{context}

User Request: {user_query}

IMPORTANT: You MUST start your response with "SRIS Juris Support states:" and follow all protocols in the system prompt above. Use proper legal formatting, analysis structure, and professional presentation.

Response:"""
            else:
                combined_prompt = f"""{self.system_prompt}

Knowledge Base Context:
{context}

User Request: {user_query}

IMPORTANT: You MUST start your response with "SRIS Juris Support states:" and follow all protocols in the system prompt above. Use proper legal formatting, analysis structure, and professional presentation.

Response:"""
        
        print(f"🔥 GENERATING RESPONSE WITH MODEL: {model_name}")
        print(f"🔥 PROMPT LENGTH: {len(combined_prompt)} characters")
        print(f"🔥 PROMPT STARTS WITH: {combined_prompt[:300]}...")
        
        try:
            if model_name == 'gemini-pro':
                model = genai.GenerativeModel(model_id)
                
                # Check if there are uploaded files for Gemini
                if hasattr(self, '_current_uploaded_files') and self._current_uploaded_files:
                    print(f"🔥 GEMINI: Processing with {len(self._current_uploaded_files)} files")
                    
                    # Prepare content with files for Gemini
                    content_parts = [combined_prompt]
                    
                    for file_info in self._current_uploaded_files:
                        if file_info['filename'].lower().endswith('.pdf'):
                            print(f"📄 Adding PDF file to Gemini: {file_info['filename']}")
                            # Upload file to Gemini
                            uploaded_file = genai.upload_file(file_info['path'])
                            content_parts.append(uploaded_file)
                    
                    response = model.generate_content(content_parts)
                else:
                    response = model.generate_content(combined_prompt)
                    
                result_text = response.text
                print(f"✅ GEMINI RESPONSE LENGTH: {len(result_text)} characters")
                return result_text
                
            elif model_name in ['claude-4-sonnet', 'claude-3-5-sonnet']:
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
                result_text = result['content'][0]['text']
                print(f"✅ CLAUDE RESPONSE LENGTH: {len(result_text)} characters")
                return result_text
                
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
                result_text = result['output']['message']['content'][0]['text']
                print(f"✅ NOVA RESPONSE LENGTH: {len(result_text)} characters")
                return result_text
                
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
            # Store uploaded files for Gemini direct access
            self._current_uploaded_files = uploaded_files
            
            # Process uploaded files (only for non-Gemini models)
            file_context = ""
            if uploaded_files and model_name != 'gemini-pro':
                print(f"🔍 Processing {len(uploaded_files)} uploaded files for {model_name}")
                file_context = self.process_uploaded_files(uploaded_files)
                print(f"🔍 Raw file_context result: '{file_context[:500]}...'")
                if file_context.strip():
                    message += f"\n\nUploaded Files Content:\n{file_context}"
                    print(f"✅ Added file context to message: {len(file_context)} characters")
                else:
                    print("❌ No file content extracted - files may be empty or unreadable")
                    # Add explicit message about file processing failure
                    message += f"\n\nNote: {len(uploaded_files)} files were uploaded but content could not be extracted. Files: {[f['filename'] for f in uploaded_files]}"
            elif uploaded_files and model_name == 'gemini-pro':
                print(f"🔥 GEMINI: Will process {len(uploaded_files)} files directly")
                message += f"\n\nFiles to analyze: {[f['filename'] for f in uploaded_files]}"
            
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
            
            print(f"Processing file: {filename} at path: {filepath}")
            
            try:
                # Check if file exists
                if not os.path.exists(filepath):
                    file_contents.append(f"File: {filename} (file not found at path: {filepath})")
                    continue
                
                if filename.lower().endswith('.pdf'):
                    # Extract text from PDF with better error handling
                    try:
                        # Try multiple PDF libraries
                        text = ""
                        
                        # Method 1: pypdf
                        try:
                            from pypdf import PdfReader
                            print(f"📄 Attempting to read PDF with pypdf: {filename}")
                            
                            with open(filepath, 'rb') as pdf_file:
                                reader = PdfReader(pdf_file)
                                print(f"📄 PDF has {len(reader.pages)} pages")
                                
                                for i, page in enumerate(reader.pages):
                                    try:
                                        page_text = page.extract_text()
                                        if page_text.strip():
                                            text += f"\n--- Page {i+1} ---\n{page_text}\n"
                                            print(f"📄 Extracted {len(page_text)} chars from page {i+1}")
                                    except Exception as page_error:
                                        print(f"❌ Error reading page {i+1}: {page_error}")
                                        
                        except ImportError:
                            print("❌ pypdf not available, trying PyPDF2")
                            # Method 2: PyPDF2 fallback
                            try:
                                import PyPDF2
                                with open(filepath, 'rb') as pdf_file:
                                    reader = PyPDF2.PdfReader(pdf_file)
                                    for i, page in enumerate(reader.pages):
                                        page_text = page.extract_text()
                                        if page_text.strip():
                                            text += f"\n--- Page {i+1} ---\n{page_text}\n"
                            except ImportError:
                                print("❌ No PDF library available")
                        
                        if text.strip():
                            clean_text = text.replace('\n\n\n', '\n\n').strip()
                            file_contents.append(f"📄 FILE: {filename}\n\nCONTENT:\n{clean_text[:4000]}...")
                            print(f"✅ Successfully extracted {len(clean_text)} characters from {filename}")
                        else:
                            # Try OCR for image-based PDFs
                            print(f"🔍 No text found, attempting OCR for {filename}")
                            ocr_text = self.extract_pdf_with_ocr(filepath, filename)
                            if ocr_text.strip():
                                file_contents.append(f"📄 FILE: {filename} (OCR)\n\nCONTENT:\n{ocr_text[:4000]}...")
                                print(f"✅ OCR extracted {len(ocr_text)} characters from {filename}")
                            else:
                                file_size = os.path.getsize(filepath)
                                file_contents.append(f"📄 FILE: {filename}\nSTATUS: PDF file detected ({file_size} bytes) but no readable text found even with OCR.")
                                print(f"⚠️ PDF {filename} has no extractable text even with OCR ({file_size} bytes)")
                                
                    except Exception as pdf_error:
                        print(f"❌ PDF processing error for {filename}: {pdf_error}")
                        file_contents.append(f"📄 FILE: {filename}\nERROR: Could not process PDF - {str(pdf_error)}")
                    
                elif filename.lower().endswith(('.txt', '.doc', '.docx')):
                    # Read text files
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    file_contents.append(f"File: {filename}\nContent: {content[:3000]}...")  # Increased limit
                    
                else:
                    file_contents.append(f"File: {filename} (unsupported format)")
                    
            except Exception as e:
                print(f"General error processing {filename}: {e}")
                file_contents.append(f"File: {filename} (error reading: {str(e)})")
        
        result = "\n\n" + "="*50 + "\n\n".join(file_contents) + "\n" + "="*50
        print(f"📋 FINAL PROCESSED CONTENT LENGTH: {len(result)} characters")
        print(f"📋 CONTENT PREVIEW: {result[:200]}...")
        return result
    
    def extract_pdf_with_ocr(self, filepath, filename):
        """Extract text from image-based PDFs using OCR"""
        try:
            # Method 1: Try pytesseract + pdf2image
            try:
                import pytesseract
                from pdf2image import convert_from_path
                from PIL import Image
                
                print(f"🔍 Converting PDF to images for OCR: {filename}")
                pages = convert_from_path(filepath, dpi=200)
                
                ocr_text = ""
                for i, page in enumerate(pages):
                    print(f"🔍 Processing page {i+1} with OCR")
                    page_text = pytesseract.image_to_string(page)
                    if page_text.strip():
                        ocr_text += f"\n--- Page {i+1} (OCR) ---\n{page_text}\n"
                
                return ocr_text
                
            except ImportError as e:
                print(f"⚠️ OCR libraries not available: {e}")
                return ""
                
        except Exception as e:
            print(f"❌ OCR processing error: {e}")
            return ""
    
    def get_available_models(self):
        return [
            {'id': 'claude-4-sonnet', 'name': 'Claude 4 Sonnet (Latest)'},
            {'id': 'claude-3-5-sonnet', 'name': 'Claude 3.5 Sonnet'},
            {'id': 'nova-pro', 'name': 'Amazon Nova Pro'},
            {'id': 'gemini-pro', 'name': 'Google Gemini 2.5 Pro'}
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
                        'model_used': item.get('model_used', 'claude-4-sonnet'),
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