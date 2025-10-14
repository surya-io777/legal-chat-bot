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
        """Load prompt file based on type - UPDATED for structured output"""
        try:
            if prompt_type == "general":
                # Clear structured formatting guidance
                return """You are a professional legal AI assistant named SRIS Juris Support.

Format ALL responses with this EXACT structure:

SRIS Juris Support states:

[Opening paragraph explaining the law/concept]

[Context paragraph about scope, eligibility, or background]

Key components of this statute include:

- **Probation:** [Detailed explanation in full paragraph form]

- **Conditions of Probation:** [Comprehensive explanation with details]

- **Dismissal of Charges:** [Complete explanation of this component]

- **Violation:** [Full explanation of consequences]

FORMATTING RULES:
- Always start with "SRIS Juris Support states:"
- Use **bold text** for component names and section headers
- Write explanations in flowing, professional paragraphs
- Use bullet points with bold headers for key components
- Maintain clear visual hierarchy
- Never collapse sections into unformatted blocks

Example response structure:

SRIS Juris Support states:

Virginia Code § 18.2-57.3 provides a legal pathway for individuals charged for the first time with assault and battery against a family or household member to have the charge dismissed. This is often referred to as a "first offender program" or "deferred disposition."

Under this statute, a court can defer the proceedings without a finding of guilt and place the accused individual on probation. To be eligible, the person generally must not have any prior convictions for similar offenses.

Key components of this statute include:

- **Probation:** The accused is placed on local community-based probation for a period of not less than two years.

- **Conditions of Probation:** The individual must maintain good behavior and successfully complete all court-ordered treatment or education programs. These programs often include anger management, substance abuse treatment, or other relevant counseling as determined by an assessment.

- **Dismissal of Charges:** Upon successful fulfillment of all terms and conditions of probation, the court will discharge the person and dismiss the proceedings. While this dismissal is without an adjudication of guilt, it is considered a conviction for the purpose of determining eligibility for this program in any subsequent proceedings.

- **Violation:** If the individual violates the terms of their probation, the court may enter an adjudication of guilt and proceed with sentencing on the original charge.

This statute allows a first-time offender the opportunity to avoid a criminal conviction for domestic assault by complying with court-supervised probation and rehabilitation."""

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

    # NEW: Universal formatting wrapper for ALL protocols
    def get_formatting_instructions(self):
        """Universal formatting rules applied to all protocols"""
        return """

=== MANDATORY OUTPUT FORMATTING (APPLIES TO ALL RESPONSES) ===

1. ALWAYS start your response with: "SRIS Juris Support states:"

2. Structure your response in clear sections with proper spacing:
   - Opening paragraph (explanation of the concept/law)
   - Context paragraph (scope, eligibility, background)
   - Detailed components with bold headers

3. When listing key components, use this EXACT format:
   - **Component Name:** Detailed explanation in paragraph form
   - **Next Component:** Full explanation with details
   - **Another Component:** Comprehensive explanation

4. FORMATTING REQUIREMENTS:
   - Use **bold text** for all section headers and key terms
   - Write in flowing, professional paragraphs (not bullet-only lists)
   - Maintain clear visual hierarchy with spacing
   - Use bullet points ONLY for organizing key components
   - Each component explanation must be in full sentence/paragraph form

5. Example structure to follow:

SRIS Juris Support states:

[Opening paragraph explaining the main concept]

[Context paragraph with relevant background]

Key components include:

- **First Component:** Complete explanation in professional paragraph form with all relevant details.

- **Second Component:** Thorough explanation with comprehensive information presented clearly.

- **Third Component:** Full details presented in structured, readable format.

[Closing paragraph if needed]

=== END FORMATTING RULES ===

"""

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

    def format_legal_response(self, response_text):
        """Ensure response has proper bold headers and structure"""
        # Ensure it starts with SRIS Juris Support states:
        if not response_text.strip().startswith("SRIS Juris Support states:"):
            response_text = "SRIS Juris Support states:\n\n" + response_text.strip()

        # Bold key section names if not already bolded
        legal_terms = [
            "Probation",
            "Conditions of Probation",
            "Dismissal of Charges",
            "Violation",
            "Key components",
            "Requirements",
            "Eligibility",
            "Core Prohibitions",
            "Penalties",
            "Elements",
            "Breakdown",
            "Analysis",
            "Overview",
            "Summary",
            "Findings",
            "Recommendations",
            "General Threats",
            "Threats on School Property",
            "Electronic Communication",
            "Reasonable Apprehension",
            "Classification",
            "Sentencing",
        ]

        for term in legal_terms:
            # Bold after bullet points if not already bolded
            response_text = re.sub(f"- {term}:", f"- **{term}:**", response_text)
            # Bold at line start if not already bolded
            response_text = re.sub(
                f"^{term}:", f"**{term}:**", response_text, flags=re.MULTILINE
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
        """Generate response using Gemini 2.5 Pro - UPDATED for consistent formatting across all protocols"""

        model_id = self.models["gemini-pro"]

        # UPDATED: All protocols now get standardized formatting
        if prompt_type == "general":
            # Use built-in structured prompt for General mode
            base_instructions = f"""{self.load_prompt_file("general")}

Chat History (for context continuity):
{chat_history}

User Instructions: {user_instructions}

User Request: {user_query}

IMPORTANT: Follow the exact formatting structure shown above. Use bold headers and clear paragraph organization."""

        else:
            # UPDATED: Custom protocols get their content + universal formatting wrapper
            custom_prompt = self.load_prompt_file(prompt_type)
            formatting_rules = self.get_formatting_instructions()

            base_instructions = f"""{custom_prompt}

{formatting_rules}

CRITICAL INSTRUCTIONS:
- Apply the custom protocol logic above
- But ALWAYS follow the mandatory formatting rules for output structure
- Combine your specialized knowledge with professional formatting
- Use **bold text** for headers and key terms
- Maintain structured, readable output

Chat History (for context continuity):
{chat_history}

User Instructions: {user_instructions}

User Request: {user_query}"""

        # Build final prompt based on request type
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
- Follow the structured format: Start with "SRIS Juris Support states:"
- Perform comprehensive, detailed analysis with bold section headers
- Use this structure:
  * Opening paragraph explaining what you're analyzing
  * Context paragraph with background
  * Key findings with **bold headers:** and detailed explanations
- Provide comprehensive analysis with detailed explanations
- Compare different sections, clauses, or documents if multiple files
- Identify legal implications, risks, and opportunities
- Include specific quotes and references from the documents
- Analyze legal language, terms, and their significance
- Highlight any unusual clauses, missing elements, or concerns
- Provide actionable insights and recommendations
- Be thorough and comprehensive in your analysis
- Maintain professional formatting throughout

Provide deep analysis:"""

        elif request_type == "document":
            combined_prompt = f"""{base_instructions}

DOCUMENT GENERATION INSTRUCTIONS:
- Start with "SRIS Juris Support states:" if providing explanation
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
- Start with "SRIS Juris Support states:"
- Create structured data without table symbols
- Use numbered lists (1., 2., 3.) for organization
- Use clear headers with **bold text**
- Present data in clean, readable format
- Use proper table formatting with clear structure
- Maintain professional formatting

Generate a well-structured table:"""

        else:
            combined_prompt = base_instructions

        print(f"🔥 GENERATING RESPONSE WITH SRIS AI ({prompt_type.upper()})")
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

            # Post-process for consistent bold formatting across all protocols
            result_text = self.format_legal_response(result_text)

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
                    message += f"\n\nFORM FILES TO FILL: {', '.join(file_list)}\nIMPORTANT: Preserve exact formatting and only fill blanks. Do not add any extra content."
                elif request_type == "analysis":
                    message += f"\n\nFILES FOR ANALYSIS: {', '.join(file_list)}\nProvide comprehensive legal analysis following the structured format with bold headers."
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
                    try:
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
            doc = SimpleDocTemplate(
                buffer, pagesize=letter, leftMargin=inch, rightMargin=inch
            )
            styles = getSampleStyleSheet()
            story = []

            # Create styles for normal and bold text
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

            # Clean content - remove any AI intro text
            clean_content = content.replace("SRIS Juris Support states:", "").strip()

            # Process lines to detect formatting
            lines = clean_content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                    continue

                # Detect markdown bold **text** and convert to ReportLab format
                if "**" in line:
                    # Convert markdown bold to ReportLab bold tags
                    line = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
                    para = Paragraph(line, normal_style)
                    story.append(para)
                elif line.isupper() and len(line) > 3:
                    # Bold formatting for ALL CAPS titles
                    para = Paragraph(f"<b>{line}</b>", bold_style)
                    story.append(para)
                elif line.startswith("- "):
                    # Bullet points - preserve bold markers
                    line = re.sub(r"- \*\*([^*]+)\*\*:", r"- <b>\1:</b>", line)
                    para = Paragraph(line, normal_style)
                    story.append(para)
                else:
                    # Regular text with preserved spacing
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
