import boto3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import uuid
from datetime import datetime

s3 = boto3.client('s3', region_name='us-east-1')
BUCKET_NAME = 'legal-chat-bot-outputs'

def generate_legal_document(content, session_id, title="Legal Document"):
    """Generate professional legal document PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Custom styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    story = []
    
    # Add title
    story.append(Paragraph("LEGAL DOCUMENT", title_style))
    story.append(Spacer(1, 20))
    
    # Add generation info
    date_para = Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles['Normal'])
    story.append(date_para)
    story.append(Paragraph(f"Document Type: {title[:50]}", styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Add content
    paragraphs = content.split('\n\n')
    for para in paragraphs:
        if para.strip():
            # Check if it's a heading (starts with numbers or all caps)
            if para.strip().isupper() or para.strip().startswith(('1.', '2.', '3.', 'I.', 'II.', 'III.')):
                p = Paragraph(para.strip(), styles['Heading2'])
            else:
                p = Paragraph(para.strip(), styles['Normal'])
            story.append(p)
            story.append(Spacer(1, 12))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Upload to S3
    file_key = f"legal-documents/{session_id}_{uuid.uuid4()}.pdf"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=file_key,
        Body=buffer.getvalue(),
        ContentType='application/pdf'
    )
    
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"

def generate_pdf(content, session_id):
    """Generate simple PDF"""
    return generate_legal_document(content, session_id, "Generated Document")

def generate_table(content, session_id):
    """Generate HTML table from content without pandas"""
    try:
        # Try to extract table-like data from content
        lines = content.split('\n')
        table_rows = []
        
        for line in lines:
            if '|' in line:
                # Table data with pipes
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    table_rows.append(cells)
        
        if not table_rows:
            # Create simple table from content
            table_rows = [
                ['Item', 'Description'],
                ['Content', content[:100] + '...']
            ]
        
        # Generate HTML table manually
        html_table = f"""
        <html>
        <head>
            <title>Legal Chat Bot - Table Output</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; font-weight: bold; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <h1>Legal Chat Bot - Table Output</h1>
            <p>Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <table>
        """
        
        # Add table rows
        for i, row in enumerate(table_rows):
            tag = 'th' if i == 0 else 'td'
            html_table += "<tr>"
            for cell in row:
                html_table += f"<{tag}>{cell}</{tag}>"
            html_table += "</tr>"
        
        html_table += """
            </table>
        </body>
        </html>
        """
        
        # Upload to S3
        file_key = f"tables/{session_id}_{uuid.uuid4()}.html"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_key,
            Body=html_table,
            ContentType='text/html'
        )
        
        return f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
        
    except Exception as e:
        print(f"Error generating table: {e}")
        return None