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
        
        # Available models - Only Gemini 2.5 Pro
        self.models = {
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
            'generate pdf', 'create pdf', 'make document', 'output pdf',
            'prepare contract', 'draft contract', 'create legal document',
            'draft', 'prepare', 'create petition', 'generate agreement',
            'make agreement', 'write document', 'compose document',
            'give it as output pdf', 'output as pdf', 'pdf file',
            'save as pdf', 'download pdf', 'export pdf'
        ]
        
        table_keywords = [
            'create table', 'generate table', 'make table',
            'create chart', 'generate chart', 'show table',
            'table format', 'tabular', 'spreadsheet'
        ]
        
        message_lower = message.lower()
        
        # Check for PDF output requests
        if any(keyword in message_lower for keyword in doc_keywords):
            print(f"🔥 DOCUMENT REQUEST DETECTED: {message_lower}")
            return 'document'
        elif any(keyword in message_lower for keyword in table_keywords):
            return 'table'
        else:
            return 'chat'
    
    def generate_response(self, user_query, context, model_name='claude-sonnet-4', request_type='chat', user_instructions=""):
        """Generate response using selected model and your prompt"""
        
        model_id = self.models.get(model_name, self.models['gemini-pro'])
        
        # Enhanced prompt for Gemini 2.5 Pro with multimodal and flexible response capabilities
        base_instructions = f"""
You are an advanced legal AI assistant with access to both knowledge base information and general legal knowledge. 

Knowledge Base Context (if available):
{context}

ADDITIONAL USER INSTRUCTIONS:
{user_instructions}

User Request: {user_query}

IMPORTANT INSTRUCTIONS:
1. You MUST start your response with "SRIS Juris Support states:"
2. Use both the knowledge base context AND your general legal knowledge to provide comprehensive answers
3. If knowledge base context is limited, supplement with your legal expertise
4. Follow the SRIS protocols from your system prompt
5. Provide professional legal analysis and formatting
"""
        
        if request_type == 'document':
            combined_prompt = f"""{self.system_prompt}

{base_instructions}

6. DOCUMENT GENERATION: Create a comprehensive legal document with proper formatting, clauses, and structure suitable for PDF generation
7. Make it professionally formatted and legally sound

Generate a complete legal document:"""
        elif request_type == 'table':
            combined_prompt = f"""{self.system_prompt}

{base_instructions}

6. TABLE GENERATION: Create structured data in table format using | symbols for columns
7. Include clear headers and organized rows
8. Make the data comprehensive and useful

Generate a well-structured table:"""
        else:
            combined_prompt = f"""{self.system_prompt}

{base_instructions}

6. Provide detailed legal analysis and advice
7. Use proper legal formatting and structure

Response:"""
        
        print(f"🔥 GENERATING RESPONSE WITH MODEL: {model_name}")
        print(f"🔥 PROMPT LENGTH: {len(combined_prompt)} characters")
        print(f"🔥 PROMPT STARTS WITH: {combined_prompt[:300]}...")
        
        try:
            # Only Gemini 2.5 Pro with multimodal capabilities
            model = genai.GenerativeModel(model_id)
            
            # Check if there are uploaded files for Gemini multimodal processing
            if hasattr(self, '_current_uploaded_files') and self._current_uploaded_files:
                print(f"🔥 GEMINI MULTIMODAL: Processing with {len(self._current_uploaded_files)} files")
                
                # Prepare content with files for Gemini
                content_parts = [combined_prompt]
                
                for file_info in self._current_uploaded_files:
                    filename = file_info['filename'].lower()
                    if filename.endswith(('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        print(f"📄 Adding multimodal file to Gemini: {file_info['filename']}")
                        # Upload file to Gemini for multimodal processing
                        uploaded_file = genai.upload_file(file_info['path'])
                        content_parts.append(uploaded_file)
                
                response = model.generate_content(content_parts)
            else:
                response = model.generate_content(combined_prompt)
                
            result_text = response.text
            print(f"✅ GEMINI RESPONSE LENGTH: {len(result_text)} characters")
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
            # Store uploaded files for Gemini multimodal processing
            self._current_uploaded_files = uploaded_files
            
            # Gemini handles all files directly with multimodal capabilities
            if uploaded_files:
                print(f"🔥 GEMINI MULTIMODAL: Will process {len(uploaded_files)} files directly")
                file_list = [f['filename'] for f in uploaded_files]
                message += f"\n\nFiles to analyze: {', '.join(file_list)}"
            
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
            
            # Generate downloadable files based on request type
            if request_type == 'document' or len(bot_response) > 500:
                try:
                    print(f"🔥 GENERATING PDF for request_type: {request_type}")
                    pdf_content = self.generate_pdf_content(bot_response, session_id, message)
                    if pdf_content:
                        output_files.append({
                            'type': 'pdf', 
                            'content': pdf_content,
                            'filename': f"legal_document_{session_id}.pdf",
                            'title': f"Legal Document - {message[:30]}..."
                        })
                        print(f"✅ PDF content generated")
                except Exception as e:
                    print(f"❌ PDF generation failed: {e}")
            
            elif request_type == 'table':
                try:
                    table_content = self.generate_table_content(bot_response, session_id)
                    if table_content:
                        output_files.append({
                            'type': 'csv', 
                            'content': table_content,
                            'filename': f"table_{session_id}.csv",
                            'title': f"Table - {message[:30]}..."
                        })
                except Exception as e:
                    print(f"❌ Table generation failed: {e}")
            
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
    
    def generate_pdf_content(self, content, session_id, title):
        """Generate PDF content for frontend download"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO
            import base64
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title_para = Paragraph(f"<b>{title[:50]}...</b>", styles['Title'])
            story.append(title_para)
            story.append(Spacer(1, 12))
            
            # Add content
            content_para = Paragraph(content.replace('\n', '<br/>'), styles['Normal'])
            story.append(content_para)
            
            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()
            
            # Return base64 encoded content for frontend
            return base64.b64encode(pdf_content).decode('utf-8')
            
        except Exception as e:
            print(f"PDF generation error: {e}")
            return None
    
    def generate_table_content(self, content, session_id):
        """Generate CSV content for frontend download"""
        try:
            # Extract table data from content
            lines = content.split('\n')
            csv_lines = []
            
            for line in lines:
                if '|' in line:
                    # Convert table format to CSV
                    csv_line = line.replace('|', ',').strip()
                    if csv_line.startswith(','):
                        csv_line = csv_line[1:]
                    if csv_line.endswith(','):
                        csv_line = csv_line[:-1]
                    csv_lines.append(csv_line)
            
            return '\n'.join(csv_lines) if csv_lines else content
            
        except Exception as e:
            print(f"Table generation error: {e}")
            return content
    
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
                        'model_used': item.get('model_used', 'gemini-pro'),
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