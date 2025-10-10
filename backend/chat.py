import boto3
import json
from datetime import datetime
import uuid
from utils import generate_pdf, generate_table, generate_legal_document
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChatService:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        # Removed bedrock_runtime - only using Gemini
        try:
            self.bedrock_agent = boto3.client(
                "bedrock-agent-runtime", region_name="us-east-1"
            )
        except Exception as e:
            print(f"Warning: bedrock-agent-runtime not available: {e}")
            self.bedrock_agent = None
        self.table = self.dynamodb.Table("Legal-bot-chat-history")
        self.knowledge_base_id = "GL3HPG5NUR"

        # Load your custom prompt
        self.system_prompt = self.load_prompt_file()

        # Configure Gemini with environment variable
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        genai.configure(api_key=gemini_api_key)

        # Available models - Only Gemini 2.5 Pro
        self.models = {"gemini-pro": "gemini-2.5-pro"}

    def load_prompt_file(self, prompt_type="general"):
        """Load prompt file based on type"""
        try:
            if prompt_type == "general":
                # Generate precise, structured responses
                return """You are a professional legal AI assistant. Respond naturally with comprehensive legal explanations.

Format your responses exactly like this structure:

Start with "SRIS Juris Support states:"

Then provide a comprehensive explanation in flowing paragraphs. When listing key components or important points, use clear section headers followed by detailed explanations.

Example structure:
- Opening paragraph explaining what the law/concept is
- Second paragraph providing context and eligibility 
- "Key components of [topic] include:" followed by detailed explanations
- Each component as a separate paragraph with header and explanation
- Closing paragraph summarizing the overall purpose/effect

Use natural, professional legal writing. No bullet points, no markdown symbols, no special formatting - just clean, structured paragraphs like a legal professional would write."""
            elif prompt_type == "singularity-counsel-8":
                prompt_path = os.path.join(os.path.dirname(__file__), "Singularity-Counsel-protocol8.0.txt")
            elif prompt_type == "singularity-counsel-11":
                prompt_path = os.path.join(os.path.dirname(__file__), "Singularity-Counsel-protocol11.0.txt")
            elif prompt_type == "juridical-singularity":
                prompt_path = os.path.join(os.path.dirname(__file__), "Juridical-singularity-protocol.txt")
            elif prompt_type == "gem1":
                prompt_path = os.path.join(os.path.dirname(__file__), "gem1.txt")
            elif prompt_type == "gem2":
                prompt_path = os.path.join(os.path.dirname(__file__), "gem2.txt")
            else:
                prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
            
            with open(prompt_path, "r", encoding="utf-8") as file:
                content = file.read()
                print(f"✅ PROMPT LOADED ({prompt_type}): {len(content)} characters from {prompt_path}")
                print(f"✅ PROMPT PREVIEW: {content[:200]}...")
                return content
        except Exception as e:
            print(f"❌ ERROR loading {prompt_type} prompt: {e}")
            return "You are a professional legal AI assistant."

    def retrieve_from_kb(self, query):
        """Retrieve relevant documents from Knowledge Base for general Q&A only"""
        if not self.bedrock_agent:
            print("Bedrock agent not available, using SRIS AI directly")
            return "", []

        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id, retrievalQuery={"text": query}
            )

            context = ""
            sources = []

            for result in response["retrievalResults"]:
                content = result["content"]["text"]
                source = result["location"]["s3Location"]["uri"]
                context += f"{content}\n\n"
                sources.append(source)

            if not context.strip():
                print("No relevant context found in knowledge base, using SRIS AI directly")
                return "", []

            return context, sources

        except Exception as e:
            print(f"KB retrieval error: {e}, using SRIS AI directly")
            return "", []

    def detect_document_request(self, message):
        """Detect if user wants document generation or analysis"""
        doc_keywords = [
            "generate", "create", "draft", "prepare", "make", "write", "compose",
            "document", "agreement", "contract", "petition", "pdf", "output",
            "generate document", "create document", "prepare document",
            "draft agreement", "create agreement", "prepare petition",
            "generate pdf", "create pdf", "make document", "output pdf",
            "prepare contract", "draft contract", "create legal document",
            "make agreement", "write document", "compose document",
            "give it as output", "output as pdf", "pdf file",
            "save as pdf", "download pdf", "export pdf", "generate output",
            "in pdf", "as pdf", "pdf format", "output in pdf",
        ]

        fill_keywords = [
            "fill", "complete", "fill out", "fill in", "complete the form",
            "fill the blanks", "fill answers", "complete answers",
            "fill the form", "complete the document", "fill missing",
            "answer the questions", "provide answers", "complete fields"
        ]

        analysis_keywords = [
            "analyze", "analysis", "review", "examine", "study", "evaluate",
            "assess", "compare", "comparison", "deep dive", "deep analysis",
            "detailed analysis", "comprehensive review", "thorough analysis",
            "extract", "summarize", "summary", "breakdown", "insights",
            "findings", "observations",
            "note about", "notes on", "report on", "overview of"
        ]

        table_keywords = [
            "create table", "generate table", "make table",
            "create chart", "generate chart", "show table",
            "table format", "tabular", "spreadsheet",
        ]

        message_lower = message.lower()

        # Check for form filling requests (highest priority)
        if any(keyword in message_lower for keyword in fill_keywords):
            print(f"🔥 FORM FILL REQUEST DETECTED: {message_lower}")
            return "fill_form"
        # Check for analysis requests
        elif any(keyword in message_lower for keyword in analysis_keywords):
            print(f"🔥 ANALYSIS REQUEST DETECTED: {message_lower}")
            return "analysis"
        # Check for document generation requests
        elif any(keyword in message_lower for keyword in doc_keywords):
            print(f"🔥 DOCUMENT REQUEST DETECTED: {message_lower}")
            return "document"
        elif any(keyword in message_lower for keyword in table_keywords):
            print(f"🔥 TABLE REQUEST DETECTED: {message_lower}")
            return "table"
        else:
            print(f"🔥 CHAT REQUEST: {message_lower}")
            return "chat"

    def generate_response(
        self,
        user_query,
        context,
        model_name="gemini-pro",
        request_type="chat",
        user_instructions="",
        chat_history="",
        prompt_type="general",
    ):
        """Generate response using Gemini 2.5 Pro"""

        model_id = self.models["gemini-pro"]

        # Load appropriate prompt based on selection
        if prompt_type == "general":
            # Use standard instructions for General (no knowledge base)
            base_instructions = f"""
You are a professional legal AI assistant. Provide comprehensive legal analysis and advice.

Chat History (for context continuity):
{chat_history}

User Instructions: {user_instructions}

User Request: {user_query}

Formatting Guidelines:
- Start responses with "SRIS Juris Support states:"
- Use clear, professional language
- Provide comprehensive explanations in flowing paragraph format
- Use **bold text** for important terms and emphasis
- Use proper legal document structure when generating documents
- Be comprehensive and precise in your analysis
- Maintain context from previous messages in this conversation
"""
        else:
            # Use PURE prompt for GEM1/GEM2 - NO extra instructions
            custom_prompt = self.load_prompt_file(prompt_type)
            base_instructions = f"""{custom_prompt}

IMPORTANT FORMATTING RULE:
- Use **bold text** for important terms and emphasis
- Use proper formatting for clear, readable output

User Request: {user_query}"""

        # For custom prompts: Use pure prompt without any additional instructions
        if prompt_type in ["singularity-counsel-8", "singularity-counsel-11", "juridical-singularity", "gem1", "gem2"]:
            combined_prompt = base_instructions
        elif prompt_type == "general":
            # For General: Add structured formatting
            combined_prompt = f"""{base_instructions}

User Request: {user_query}

Respond naturally and comprehensively."""
        else:
            # For other request types: Add specific instructions
            if request_type == "fill_form":
                combined_prompt = f"""{base_instructions}

FORM FILLING INSTRUCTIONS:
- PRESERVE the EXACT original formatting, titles, bold text, and structure
- ONLY fill in blanks, empty fields, or answer questions
- DO NOT add any extra content, headers, explanations, or recommendations
- DO NOT change any existing text, formatting, or structure
- Keep all original CAPITAL LETTERS, bold formatting, and spacing exactly as provided
- Fill blanks with appropriate legal information based on context
- Maintain the exact same document layout and appearance
- NO additional analysis, insights, or commentary
- Output ONLY the original document with filled blanks

Fill the form exactly as provided:"""
            elif request_type == "analysis":
                combined_prompt = f"""{base_instructions}

DEEP ANALYSIS INSTRUCTIONS:
- Perform comprehensive, detailed analysis of all uploaded content
- Provide comprehensive analysis with detailed explanations
- Compare different sections, clauses, or documents if multiple files
- Identify legal implications, risks, and opportunities
- Provide detailed breakdown of structure, content, and meaning
- Include specific quotes and references from the documents
- Analyze legal language, terms, and their significance
- Compare with standard legal practices and requirements
- Highlight any unusual clauses, missing elements, or concerns
- Provide actionable insights and recommendations
- Be thorough and comprehensive in your analysis

Provide deep analysis:"""
            elif request_type == "document":
                combined_prompt = f"""{base_instructions}

DOCUMENT GENERATION INSTRUCTIONS:
- Create a comprehensive legal document with proper formatting
- Use CAPITAL LETTERS for main titles and section headers
- Structure with numbered clauses (1., 2., 3.)
- Use proper legal indentation and spacing
- Use **bold text** for emphasis and important terms
- Use proper formatting for professional appearance
- Make it professionally formatted and legally sound

Generate a complete legal document:"""
            elif request_type == "table":
                combined_prompt = f"""{base_instructions}

TABLE GENERATION INSTRUCTIONS:
- Create structured data without table symbols
- Use numbered lists (1., 2., 3.) for organization
- Use clear headers in CAPITAL LETTERS
- Present data in clean, readable format
- Use proper table formatting with clear structure
- Use **bold text** for headers and emphasis

Generate a well-structured table:"""
            else:
                combined_prompt = f"""{base_instructions}

RESPONSE INSTRUCTIONS:
- Provide detailed legal analysis and advice
- Use numbered lists (1., 2., 3.) for sequential information
- Write in flowing, comprehensive paragraphs
- Structure in clear, readable paragraphs
- Use **bold text** for emphasis and important terms
- Use proper formatting for professional appearance

Response:"""

        print(f"🔥 GENERATING RESPONSE WITH SRIS AI SYSTEM: {model_name}")
        print(f"🔥 PROMPT LENGTH: {len(combined_prompt)} characters")
        print(f"🔥 PROMPT STARTS WITH: {combined_prompt[:300]}...")

        try:
            # Only Gemini 2.5 Pro with multimodal capabilities
            model = genai.GenerativeModel(model_id)

            # Check if there are uploaded files for Gemini multimodal processing
            if (
                hasattr(self, "_current_uploaded_files")
                and self._current_uploaded_files
            ):
                print(
                    f"🔥 SRIS AI MULTIMODAL: Processing with {len(self._current_uploaded_files)} files"
                )

                # Prepare content with files for Gemini
                content_parts = [combined_prompt]

                for file_info in self._current_uploaded_files:
                    filename = file_info["filename"].lower()
                    if filename.endswith(
                        (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
                    ):
                        print(
                            f"📄 Adding multimodal file to SRIS AI: {file_info['filename']}"
                        )
                        # Upload file to Gemini for multimodal processing
                        uploaded_file = genai.upload_file(file_info["path"])
                        content_parts.append(uploaded_file)

                response = model.generate_content(content_parts)
            else:
                response = model.generate_content(combined_prompt)

            result_text = response.text
            print(f"✅ SRIS AI RESPONSE LENGTH: {len(result_text)} characters")
            return result_text

        except Exception as e:
            return f"Error generating response: {str(e)}"

    def send_message(
        self,
        user_id,
        message,
        session_id=None,
        model_name="gemini-pro",
        user_instructions="",
        uploaded_files=[],
        prompt_type="general",
    ):
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        timestamp = datetime.now().isoformat()

        # Detect request type
        request_type = self.detect_document_request(message)

        # Get chat history for context
        chat_history = self.get_chat_history(user_id, session_id)

        # Save user message
        self.table.put_item(
            Item={
                "user_id": user_id,
                "message_timestamp": timestamp,
                "session_id": session_id,
                "message_type": "user",
                "message_content": message,
                "session_title": message[:50] + "..." if len(message) > 50 else message,
                "model_used": model_name,
                "request_type": request_type,
                "user_instructions": user_instructions,
            }
        )

        try:
            # Store uploaded files for Gemini multimodal processing
            self._current_uploaded_files = uploaded_files

            # KNOWLEDGE BASE DISABLED - All modes use pure prompts
            print(f"🔥 PURE PROMPT MODE ({prompt_type.upper()}): Knowledge base disabled")
            kb_context, sources = "", []
            
            # Add file info if files uploaded
            if uploaded_files:
                print(
                    f"🔥 SRIS AI MULTIMODAL: Will process {len(uploaded_files)} files directly"
                )
                file_list = [f["filename"] for f in uploaded_files]
                if request_type == "fill_form":
                    message += f"\n\nFORM FILES TO FILL: {', '.join(file_list)}\nIMPORTANT: Preserve exact formatting and only fill blanks. Do not add any extra content."
                elif request_type == "analysis":
                    message += f"\n\nFILES FOR ANALYSIS: {', '.join(file_list)}\nProvide comprehensive legal analysis in detailed paragraph format. Explain thoroughly without using bullet points."
                else:
                    message += f"\n\nFiles to analyze: {', '.join(file_list)}"

            # Generate response with your prompt and chat history
            bot_response = self.generate_response(
                message,
                kb_context,
                model_name,
                request_type,
                user_instructions,
                chat_history,
                prompt_type,
            )

            # Save assistant response
            assistant_timestamp = datetime.now().isoformat()
            self.table.put_item(
                Item={
                    "user_id": user_id,
                    "message_timestamp": assistant_timestamp,
                    "session_id": session_id,
                    "message_type": "assistant",
                    "message_content": bot_response,
                    "session_title": (
                        message[:50] + "..." if len(message) > 50 else message
                    ),
                    "model_used": model_name,
                    "sources": sources,
                    "request_type": request_type,
                }
            )

            # Generate output files based on request type
            output_files = []

            # Generate downloadable files when explicitly requested OR when response is long
            if request_type in ["document", "analysis"] or len(bot_response) > 1000:
                try:
                    print(
                        f"🔥 GENERATING PDF for request (type: {request_type}, length: {len(bot_response)})"
                    )
                    pdf_content = self.generate_pdf_content(
                        bot_response, session_id, message
                    )
                    if pdf_content:
                        filename = f"analysis_report_{session_id}.pdf" if request_type == "analysis" else f"legal_document_{session_id}.pdf"
                        title = f"Analysis Report - {message[:30]}..." if request_type == "analysis" else f"Legal Document - {message[:30]}..."
                        output_files.append(
                            {
                                "type": "pdf",
                                "content": pdf_content,
                                "filename": filename,
                                "title": title,
                            }
                        )
                        print(f"✅ PDF content generated")
                except Exception as e:
                    print(f"❌ PDF generation failed: {e}")

            elif request_type == "table":
                try:
                    table_content = self.generate_table_content(
                        bot_response, session_id
                    )
                    if table_content:
                        output_files.append(
                            {
                                "type": "csv",
                                "content": table_content,
                                "filename": f"table_{session_id}.csv",
                                "title": f"Table - {message[:30]}...",
                            }
                        )
                except Exception as e:
                    print(f"❌ Table generation failed: {e}")

            return {
                "success": True,
                "response": bot_response,
                "session_id": session_id,
                "model_used": model_name,
                "sources": sources,
                "request_type": request_type,
                "output_files": output_files,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            # Clean up temporary files
            for file_info in uploaded_files:
                try:
                    if os.path.exists(file_info["path"]):
                        os.remove(file_info["path"])
                except:
                    pass

    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and extract content"""
        file_contents = []

        for file_info in uploaded_files:
            filename = file_info["filename"]
            filepath = file_info["path"]

            print(f"Processing file: {filename} at path: {filepath}")

            try:
                # Check if file exists
                if not os.path.exists(filepath):
                    file_contents.append(
                        f"File: {filename} (file not found at path: {filepath})"
                    )
                    continue

                if filename.lower().endswith(".pdf"):
                    # Extract text from PDF with better error handling
                    try:
                        # Try multiple PDF libraries
                        text = ""

                        # Method 1: pypdf
                        try:
                            from pypdf import PdfReader

                            print(f"📄 Attempting to read PDF with pypdf: {filename}")

                            with open(filepath, "rb") as pdf_file:
                                reader = PdfReader(pdf_file)
                                print(f"📄 PDF has {len(reader.pages)} pages")

                                for i, page in enumerate(reader.pages):
                                    try:
                                        page_text = page.extract_text()
                                        if page_text.strip():
                                            text += (
                                                f"\n--- Page {i+1} ---\n{page_text}\n"
                                            )
                                            print(
                                                f"📄 Extracted {len(page_text)} chars from page {i+1}"
                                            )
                                    except Exception as page_error:
                                        print(
                                            f"❌ Error reading page {i+1}: {page_error}"
                                        )

                        except ImportError:
                            print("❌ pypdf not available, trying PyPDF2")
                            # Method 2: PyPDF2 fallback
                            try:
                                import PyPDF2

                                with open(filepath, "rb") as pdf_file:
                                    reader = PyPDF2.PdfReader(pdf_file)
                                    for i, page in enumerate(reader.pages):
                                        page_text = page.extract_text()
                                        if page_text.strip():
                                            text += (
                                                f"\n--- Page {i+1} ---\n{page_text}\n"
                                            )
                            except ImportError:
                                print("❌ No PDF library available")

                        if text.strip():
                            clean_text = text.replace("\n\n\n", "\n\n").strip()
                            file_contents.append(
                                f"📄 FILE: {filename}\n\nCONTENT:\n{clean_text[:4000]}..."
                            )
                            print(
                                f"✅ Successfully extracted {len(clean_text)} characters from {filename}"
                            )
                        else:
                            # Try OCR for image-based PDFs
                            print(f"🔍 No text found, attempting OCR for {filename}")
                            ocr_text = self.extract_pdf_with_ocr(filepath, filename)
                            if ocr_text.strip():
                                file_contents.append(
                                    f"📄 FILE: {filename} (OCR)\n\nCONTENT:\n{ocr_text[:4000]}..."
                                )
                                print(
                                    f"✅ OCR extracted {len(ocr_text)} characters from {filename}"
                                )
                            else:
                                file_size = os.path.getsize(filepath)
                                file_contents.append(
                                    f"📄 FILE: {filename}\nSTATUS: PDF file detected ({file_size} bytes) but no readable text found even with OCR."
                                )
                                print(
                                    f"⚠️ PDF {filename} has no extractable text even with OCR ({file_size} bytes)"
                                )

                    except Exception as pdf_error:
                        print(f"❌ PDF processing error for {filename}: {pdf_error}")
                        file_contents.append(
                            f"📄 FILE: {filename}\nERROR: Could not process PDF - {str(pdf_error)}"
                        )

                elif filename.lower().endswith((".txt", ".doc", ".docx")):
                    # Read text files
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_contents.append(
                        f"File: {filename}\nContent: {content[:3000]}..."
                    )  # Increased limit

                else:
                    file_contents.append(f"File: {filename} (unsupported format)")

            except Exception as e:
                print(f"General error processing {filename}: {e}")
                file_contents.append(f"File: {filename} (error reading: {str(e)})")

        result = "\n\n" + "=" * 50 + "\n\n".join(file_contents) + "\n" + "=" * 50
        print(f"📋 FINAL PROCESSED CONTENT LENGTH: {len(result)} characters")
        print(f"📋 CONTENT PREVIEW: {result[:200]}...")
        return result

    def generate_pdf_content(self, content, session_id, title):
        """Generate PDF content preserving exact formatting with bold text"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from io import BytesIO
            import base64
            import re

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=inch, rightMargin=inch)
            styles = getSampleStyleSheet()
            story = []

            # Create styles for normal and bold text
            normal_style = ParagraphStyle(
                'NormalStyle',
                parent=styles['Normal'],
                fontName='Times-Roman',
                fontSize=11,
                leading=14,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=6,
                spaceBefore=0
            )
            
            bold_style = ParagraphStyle(
                'BoldStyle',
                parent=styles['Normal'],
                fontName='Times-Bold',
                fontSize=12,
                leading=16,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=8,
                spaceBefore=4
            )

            # Clean content - remove any AI intro text
            clean_content = content.replace('SRIS Juris Support states:', '').strip()
            
            # Process lines to detect formatting
            lines = clean_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                    continue
                
                # Detect if line should be bold (all caps, titles, headers)
                if (line.isupper() and len(line) > 3) or \
                   any(word in line.upper() for word in ['AGREEMENT', 'CONTRACT', 'PETITION', 'WHEREAS', 'NOW THEREFORE']):
                    # Bold formatting for titles and headers
                    para = Paragraph(f"<b>{line}</b>", bold_style)
                    story.append(para)
                else:
                    # Regular text with preserved spacing
                    # Convert multiple spaces to non-breaking spaces
                    formatted_line = line.replace('  ', '&nbsp;&nbsp;')
                    para = Paragraph(formatted_line, normal_style)
                    story.append(para)

            doc.build(story)
            pdf_content = buffer.getvalue()
            buffer.close()

            return base64.b64encode(pdf_content).decode("utf-8")

        except Exception as e:
            print(f"PDF generation error: {e}")
            return None

    def generate_table_content(self, content, session_id):
        """Generate CSV content for frontend download"""
        try:
            # Extract table data from content
            lines = content.split("\n")
            csv_lines = []

            for line in lines:
                if "|" in line:
                    # Convert table format to CSV
                    csv_line = line.replace("|", ",").strip()
                    if csv_line.startswith(","):
                        csv_line = csv_line[1:]
                    if csv_line.endswith(","):
                        csv_line = csv_line[:-1]
                    csv_lines.append(csv_line)

            return "\n".join(csv_lines) if csv_lines else content

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
        return [{"id": "gemini-pro", "name": "SRIS Legal AI System"}]

    def get_user_sessions(self, user_id):
        try:
            response = self.table.query(
                KeyConditionExpression="user_id = :uid",
                ExpressionAttributeValues={":uid": user_id},
                ScanIndexForward=False,
            )

            sessions = {}
            for item in response["Items"]:
                sid = item["session_id"]
                if sid not in sessions:
                    sessions[sid] = {
                        "session_id": sid,
                        "title": item["session_title"],
                        "last_message": item["message_content"][:100],
                        "timestamp": item["message_timestamp"],
                        "model_used": item.get("model_used", "gemini-pro"),
                        "request_type": item.get("request_type", "chat"),
                    }

            return {"success": True, "sessions": list(sessions.values())}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session_messages(self, user_id, session_id):
        try:
            response = self.table.query(
                KeyConditionExpression="user_id = :uid",
                FilterExpression="session_id = :sid",
                ExpressionAttributeValues={":uid": user_id, ":sid": session_id},
                ScanIndexForward=True,
            )

            return {"success": True, "messages": response["Items"]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_chat_history(self, user_id, session_id, limit=10):
        """Get recent chat history for context"""
        try:
            response = self.table.query(
                KeyConditionExpression="user_id = :uid",
                FilterExpression="session_id = :sid",
                ExpressionAttributeValues={":uid": user_id, ":sid": session_id},
                ScanIndexForward=False,
                Limit=limit * 2,  # Get more to account for user/assistant pairs
            )

            messages = response["Items"]
            if not messages:
                return ""

            # Format recent messages for context
            history_text = "\nRecent conversation:\n"
            for msg in reversed(messages[-limit:]):
                role = "User" if msg["message_type"] == "user" else "Assistant"
                content = (
                    msg["message_content"][:200] + "..."
                    if len(msg["message_content"]) > 200
                    else msg["message_content"]
                )
                history_text += f"{role}: {content}\n"

            return history_text

        except Exception as e:
            print(f"Error getting chat history: {e}")
            return ""
