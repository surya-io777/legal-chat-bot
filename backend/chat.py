import boto3
import json
from datetime import datetime
import uuid
from utils import generate_pdf, generate_table, generate_legal_document
import os
import google.generativeai as genai
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()


class ChatService:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
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
        """Load prompt file based on type - FIXED to separate example from actual response"""
        try:
            if prompt_type == "general":
                # FIXED: Clear formatting instructions with explicit markdown structure for Gemini
                return """You are a professional legal AI assistant named SRIS Juris Support.

MANDATORY RESPONSE STRUCTURE (FOLLOW EXACTLY FOR ALL QUERIES):

SRIS Juris Support states:

[First paragraph: Provide a clear, comprehensive explanation of what the user asked about. Answer their specific question directly without referencing examples.]

[Second paragraph: Give context, background, eligibility requirements, or scope of the legal concept/statute being discussed.]

Key components of this topic include:

- **Component 1:** [Detailed explanation in full paragraph form - answer based on user's actual question]

- **Component 2:** [Comprehensive explanation with relevant details for the specific query]

- **Component 3:** [Complete explanation relevant to the user's question]

- **Component 4:** [Additional relevant component based on the actual query]

IMPORTANT GUIDELINES:
- ALWAYS start with "SRIS Juris Support states:" 
- Answer the USER'S SPECIFIC QUESTION - do not use examples from the prompt
- Use **bold text** only for component headers and key legal terms
- Write ALL explanations in flowing, professional paragraphs (full sentences)
- Create 4 bullet points with bold headers that are RELEVANT to the user's actual question
- If the question is general, provide general components; if specific, focus on those details
- Never copy or reference the formatting example - that was just to show structure
- Maintain clear visual hierarchy with proper spacing between sections
- Use **bold** markdown (**) for headers like **Key components of this topic include:** and component names

FORMATTING EXAMPLE (DO NOT USE THIS CONTENT - JUST THE STRUCTURE):
[This is just to show the format - replace with actual answer to user's question]

SRIS Juris Support states:

[Your actual answer to the user's specific question goes here]

[Your context and background for the user's question goes here]

Key components of this topic include:

- **Actual Component from User's Question:** [Your relevant explanation]
- **Another Relevant Component:** [Your relevant explanation]
- **Third Relevant Component:** [Your relevant explanation]
- **Fourth Relevant Component:** [Your relevant explanation]

CRITICAL: The example above is ONLY for formatting. Your actual response must address the user's specific question about Virginia Code or any other legal topic they ask about."""
            elif prompt_type == "singularity-counsel-8":
                prompt_path = os.path.join(
                    os.path.dirname(__file__), "Singularity-Counsel-protocol8.0.txt"
                )
            elif prompt_type == "singularity-counsel-11":
                prompt_path = os.path.join(
                    os.path.dirname(__file__), "Singularity-Counsel-protocol11.0.txt"
                )
            elif prompt_type == "juridical-singularity":
                prompt_path = os.path.join(
                    os.path.dirname(__file__), "Juridical-singularity-protocol.txt"
                )
            elif prompt_type == "gem1":
                prompt_path = os.path.join(os.path.dirname(__file__), "gem1.txt")
            elif prompt_type == "gem2":
                prompt_path = os.path.join(os.path.dirname(__file__), "gem2.txt")
            else:
                prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")

            with open(prompt_path, "r", encoding="utf-8") as file:
                content = file.read()
                print(
                    f"✅ PROMPT LOADED ({prompt_type}): {len(content)} characters from {prompt_path}"
                )
                print(f"✅ PROMPT PREVIEW: {content[:200]}...")
                return content
        except Exception as e:
            print(f"❌ ERROR loading {prompt_type} prompt: {e}")
            return "You are a professional legal AI assistant."

    # UPDATED: Universal formatting wrapper - FIXED to emphasize actual query response
    def get_formatting_instructions(self):
        """Universal formatting rules applied to all protocols - FIXED"""
        return """

=== MANDATORY OUTPUT FORMATTING (APPLIES TO ALL RESPONSES) ===

CRITICAL INSTRUCTION: Answer the USER'S SPECIFIC QUESTION directly. Do not copy examples from the prompt.

1. ALWAYS start your response with: "SRIS Juris Support states:"

2. Structure your response in clear sections with proper spacing:
   - **Opening paragraph:** Answer the user's question directly and comprehensively
   - **Context paragraph:** Provide relevant background, scope, or eligibility for the specific topic
   - **Key components:** Use 4 bullet points with bold headers RELEVANT to the user's actual question

3. When listing key components, use this EXACT format (but with content relevant to user's query):
   - **Component Name:** Detailed explanation in paragraph form specific to user's question
   - **Next Component:** Full explanation with details relevant to the actual query
   - **Another Component:** Comprehensive explanation for the specific topic asked about
   - **Additional Component:** Relevant information based on user's actual request

4. FORMATTING REQUIREMENTS:
   - Use **bold text** for all section headers and key legal terms only
   - Write in flowing, professional paragraphs (not bullet-only lists)
   - Maintain clear visual hierarchy with spacing
   - Use bullet points ONLY for organizing key components
   - Each component explanation must be in full sentence/paragraph form
   - **NEVER copy the formatting example content - only use the structure**

5. RESPONSE FLOW FOR GENERAL QUESTIONS:
   - For "What is VA Code?": Explain what Virginia Code is generally
   - For specific sections: Focus on that section's requirements
   - For analysis requests: Structure analysis around the specific document/topic
   - Always adapt components to the actual user's question

=== END FORMATTING RULES ===
"""

    def detect_query_type(self, user_query):
        """NEW: Detect the type of query to guide component generation"""
        query_lower = user_query.lower()

        # General VA Code questions
        if any(
            term in query_lower
            for term in ["va code", "virginia code", "what is", "explain", "overview"]
        ):
            return "general_va_code"
        # Specific code sections
        elif any(
            term in query_lower
            for term in ["§", "section", "18.2", "19.2", "code section"]
        ):
            return "specific_code"
        # Analysis requests
        elif "analyze" in query_lower or "review" in query_lower:
            return "analysis"
        # Document generation
        elif any(term in query_lower for term in ["generate", "create", "draft"]):
            return "document"
        else:
            return "general_legal"

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
                print(
                    "No relevant context found in knowledge base, using SRIS AI directly"
                )
                return "", []

            return context, sources

        except Exception as e:
            print(f"KB retrieval error: {e}, using SRIS AI directly")
            return "", []

    def detect_document_request(self, message):
        """Detect if user wants document generation or analysis"""
        doc_keywords = [
            "generate",
            "create",
            "draft",
            "prepare",
            "make",
            "write",
            "compose",
            "document",
            "agreement",
            "contract",
            "petition",
            "pdf",
            "output",
            "generate document",
            "create document",
            "prepare document",
            "draft agreement",
            "create agreement",
            "prepare petition",
            "generate pdf",
            "create pdf",
            "make document",
            "output pdf",
            "prepare contract",
            "draft contract",
            "create legal document",
            "make agreement",
            "write document",
            "compose document",
            "give it as output",
            "output as pdf",
            "pdf file",
            "save as pdf",
            "download pdf",
            "export pdf",
            "generate output",
            "in pdf",
            "as pdf",
            "pdf format",
            "output in pdf",
        ]

        fill_keywords = [
            "fill",
            "complete",
            "fill out",
            "fill in",
            "complete the form",
            "fill the blanks",
            "fill answers",
            "complete answers",
            "fill the form",
            "complete the document",
            "fill missing",
            "answer the questions",
            "provide answers",
            "complete fields",
        ]

        analysis_keywords = [
            "analyze",
            "analysis",
            "review",
            "examine",
            "study",
            "evaluate",
            "assess",
            "compare",
            "comparison",
            "deep dive",
            "deep analysis",
            "detailed analysis",
            "comprehensive review",
            "thorough analysis",
            "extract",
            "summarize",
            "summary",
            "breakdown",
            "insights",
            "findings",
            "observations",
            "note about",
            "notes on",
            "report on",
            "overview of",
        ]

        table_keywords = [
            "create table",
            "generate table",
            "make table",
            "create chart",
            "generate chart",
            "show table",
            "table format",
            "tabular",
            "spreadsheet",
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

    def format_legal_response(self, response_text, user_query):
        """CORRECTED: Minimal post-processing to preserve Gemini's natural markdown structure"""
        # Ensure it starts with the exact header if missing
        if not response_text.strip().startswith("SRIS Juris Support states:"):
            response_text = "SRIS Juris Support states:\n\n" + response_text.strip()

        # Ensure the key components header exists and is bolded if needed
        if "Key components of this topic include:" not in response_text:
            # Insert it after the second paragraph if structure is broken
            paragraphs = re.split(r"\n\s*\n", response_text.strip())
            if len(paragraphs) >= 2:
                response_text = (
                    paragraphs[0]
                    + "\n\n"
                    + paragraphs[1]
                    + "\n\n**Key components of this topic include:**\n\n"
                    + "\n\n".join(paragraphs[2:])
                )

        # Clean up excessive newlines but preserve spacing
        response_text = re.sub(r"\n{3,}", "\n\n", response_text)

        # Ensure bullet points start with - ** if they don't already have proper bolding
        response_text = re.sub(
            r"^- ([^*]+):(?=\s|$)", r"- **\1:**", response_text, flags=re.MULTILINE
        )

        return response_text

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
        """Generate response using Gemini 2.5 Pro - FIXED to focus on user's actual question"""

        model_id = self.models["gemini-pro"]

        # UPDATED: Dynamic query detection and focused instructions
        query_type = self.detect_query_type(user_query)

        if prompt_type == "general":
            # FIXED: Emphasize answering the actual question
            base_instructions = f"""{self.load_prompt_file("general")}

CRITICAL FOCUS INSTRUCTIONS:
- The user's question is: "{user_query}"
- Provide a DIRECT answer to this specific question
- Do NOT use or reference any examples from the prompt
- Base your components on the actual Virginia Code topic being asked about
- If asking about "VA Code" generally: Explain what Virginia Code is
- If asking about specific sections: Focus on those sections
- Generate 4 relevant components based on the actual query
- Use **bold** markdown for component headers like **Component Name:**

Chat History (for context continuity):
{chat_history}

User Instructions: {user_instructions}

User Request: {user_query}

QUERY TYPE DETECTED: {query_type}
IMPORTANT: Answer the user's specific question using the structure above."""

        else:
            # For custom protocols: Keep their logic but add query focus
            custom_prompt = self.load_prompt_file(prompt_type)
            formatting_rules = self.get_formatting_instructions()

            base_instructions = f"""{custom_prompt}

{formatting_rules}

QUERY FOCUS INSTRUCTIONS:
- User's specific question: "{user_query}"
- Apply your specialized protocol to answer THIS question
- Use the mandatory formatting structure for the output
- Generate components RELEVANT to the actual query, not examples
- For general VA Code questions: Explain the code structure and purpose
- For specific code sections: Focus on those sections' requirements and implications
- Use **bold** markdown for headers and components

Chat History (for context continuity):
{chat_history}

User Instructions: {user_instructions}

User Request: {user_query}

QUERY TYPE: {query_type} - Answer this specific question using your protocol."""

        # Build final prompt based on request type
        if request_type == "fill_form":
            combined_prompt = f"""{base_instructions}

FORM FILLING INSTRUCTIONS (PRESERVE ORIGINAL):
- Fill ONLY the blanks in the provided document
- Maintain exact original formatting, structure, and styling
- Do not add explanations or new sections
- Output only the completed form"""

        elif request_type == "analysis":
            combined_prompt = f"""{base_instructions}

ANALYSIS STRUCTURE (USE FOR DOCUMENT REVIEW):
SRIS Juris Support states:

[Opening: What this document is and its main purpose]

[Context: Background and relevant legal framework]

**Key components of this analysis include:**

- **Document Structure:** [Analysis of organization and layout]
- **Legal Provisions:** [Key legal clauses and their implications]  
- **Risk Assessment:** [Potential legal risks and concerns]
- **Recommendations:** [Actionable suggestions for improvement]

Analyze the specific document uploaded."""

        elif request_type == "document":
            combined_prompt = f"""{base_instructions}

LEGAL DOCUMENT GENERATION:
- Create professional legal document for: {user_query}
- Use proper legal formatting with numbered sections
- Include all necessary clauses relevant to the request
- Maintain SRIS Juris Support professional standards"""

        elif request_type == "table":
            combined_prompt = f"""{base_instructions}

DATA PRESENTATION FORMAT:
SRIS Juris Support states:

[Brief introduction to the data being presented]

**Key data components include:**

- **Data Category 1:** [Description and details]
- **Data Category 2:** [Description and details] 
- **Data Category 3:** [Description and details]
- **Data Category 4:** [Description and details]

Present the information in clear, structured format."""

        else:
            # For general chat - emphasize query focus
            combined_prompt = f"""{base_instructions}

RESPONSE GUIDANCE:
- Answer the user's question: "{user_query}"
- Use the 4-component structure relevant to Virginia Code or the specific legal topic
- Make each component directly responsive to the actual query
- Do not reference or copy any prompt examples
- Use **bold** markdown for all headers like **Key components of this topic include:** and component names"""

        print(f"🔥 GENERATING RESPONSE FOR QUERY: {user_query[:100]}...")
        print(f"🔥 QUERY TYPE: {query_type}")
        print(f"🔥 PROMPT TYPE: {prompt_type}")
        print(f"🔥 PROMPT LENGTH: {len(combined_prompt)} characters")

        try:
            model = genai.GenerativeModel(model_id)

            # Check if there are uploaded files for Gemini multimodal processing
            if (
                hasattr(self, "_current_uploaded_files")
                and self._current_uploaded_files
            ):
                print(
                    f"🔥 SRIS AI MULTIMODAL: Processing with {len(self._current_uploaded_files)} files"
                )

                content_parts = [combined_prompt]

                for file_info in self._current_uploaded_files:
                    filename = file_info["filename"].lower()
                    if filename.endswith(
                        (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
                    ):
                        print(
                            f"📄 Adding multimodal file to SRIS AI: {file_info['filename']}"
                        )
                        uploaded_file = genai.upload_file(file_info["path"])
                        content_parts.append(uploaded_file)

                response = model.generate_content(content_parts)
            else:
                response = model.generate_content(combined_prompt)

            result_text = response.text

            # FIXED: Pass user_query to format_legal_response for better context
            result_text = self.format_legal_response(result_text, user_query)

            print(f"✅ RESPONSE GENERATED: {len(result_text)} characters")
            return result_text

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    # Rest of your methods remain exactly the same
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
            print(
                f"🔥 PURE PROMPT MODE ({prompt_type.upper()}): Knowledge base disabled"
            )
            kb_context, sources = "", []

            # Add file info if files uploaded
            if uploaded_files:
                print(
                    f"🔥 SRIS AI MULTIMODAL: Will process {len(uploaded_files)} files directly"
                )
                file_list = [f["filename"] for f in uploaded_files]
                if request_type == "fill_form":
                    message += f"\n\nFORM FILES TO FILL: {', '.join(file_list)}\nIMPORTANT: Preserve exact formatting and only fill blanks."
                elif request_type == "analysis":
                    message += f"\n\nFILES FOR ANALYSIS: {', '.join(file_list)}\nProvide comprehensive legal analysis following the structured format."
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
                        filename = (
                            f"analysis_report_{session_id}.pdf"
                            if request_type == "analysis"
                            else f"legal_document_{session_id}.pdf"
                        )
                        title = (
                            f"Analysis Report - {message[:30]}..."
                            if request_type == "analysis"
                            else f"Legal Document - {message[:30]}..."
                        )
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

    # Include all your other existing methods (process_uploaded_files, generate_pdf_content, etc.)
    # They remain exactly the same as in your previous working version
    def process_uploaded_files(self, uploaded_files):
        """Process uploaded files and extract content"""
        file_contents = []

        for file_info in uploaded_files:
            filename = file_info["filename"]
            filepath = file_info["path"]

            print(f"Processing file: {filename} at path: {filepath}")

            try:
                if not os.path.exists(filepath):
                    file_contents.append(
                        f"File: {filename} (file not found at path: {filepath})"
                    )
                    continue

                if filename.lower().endswith(".pdf"):
                    try:
                        text = ""
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
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_contents.append(
                        f"File: {filename}\nContent: {content[:3000]}..."
                    )

                else:
                    file_contents.append(f"File: {filename} (unsupported format)")

            except Exception as e:
                print(f"General error processing {filename}: {e}")
                file_contents.append(f"File: {filename} (error reading: {str(e)})")

        result = (
            "\n\n" + "=" * 50 + "\n\n" + "\n\n".join(file_contents) + "\n" + "=" * 50
        )
        print(f"📋 FINAL PROCESSED CONTENT LENGTH: {len(result)} characters")
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
            doc = SimpleDocTemplate(
                buffer, pagesize=letter, leftMargin=inch, rightMargin=inch
            )
            styles = getSampleStyleSheet()
            story = []

            normal_style = ParagraphStyle(
                "NormalStyle",
                parent=styles["Normal"],
                fontName="Times-Roman",
                fontSize=11,
                leading=14,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=6,
                spaceBefore=0,
            )

            bold_style = ParagraphStyle(
                "BoldStyle",
                parent=styles["Normal"],
                fontName="Times-Bold",
                fontSize=12,
                leading=16,
                leftIndent=0,
                rightIndent=0,
                spaceAfter=8,
                spaceBefore=4,
            )

            clean_content = content.replace("SRIS Juris Support states:", "").strip()
            lines = clean_content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                    continue

                if "**" in line:
                    line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
                    para = Paragraph(line, normal_style)
                    story.append(para)
                elif line.isupper() and len(line) > 3:
                    para = Paragraph(f"<b>{line}</b>", bold_style)
                    story.append(para)
                elif line.startswith("- "):
                    line = re.sub(r"- \*\*([^*]+)\*\*:", r"- <b>\1:</b>", line)
                    para = Paragraph(line, normal_style)
                    story.append(para)
                else:
                    formatted_line = line.replace("  ", "&nbsp;&nbsp;")
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
            lines = content.split("\n")
            csv_lines = []

            for line in lines:
                if "|" in line:
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
                Limit=limit * 2,
            )

            messages = response["Items"]
            if not messages:
                return ""

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
