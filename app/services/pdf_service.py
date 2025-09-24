"""
PDF generation service for invoices and reports
"""
import os
import io
from datetime import datetime
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from app.models.billing import Invoice, InvoiceItem
from app.models.user import User


class PDFInvoiceService:
    """Service for generating PDF invoices"""
    
    # Company information
    COMPANY_INFO = {
        "name": "AgnoShin",
        "address": "Ayodhya Colony , Velacherry",
        "city": "Chennnai - 600042",
        "phone": "+1 (555) 123-4567",
        "email": "billing@agnoshin.com",
        "website": "www.agnoshin.com"
    }
    
    @classmethod
    def generate_invoice_pdf(
        cls,
        invoice: Invoice,
        user: User,
        invoice_items: list[InvoiceItem],
        output_path: Optional[str] = None
    ) -> bytes:
        """Generate PDF invoice and return as bytes"""
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb')
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#374151')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Add company header
        story.append(Paragraph(cls.COMPANY_INFO["name"], title_style))
        story.append(Paragraph(f"{cls.COMPANY_INFO['address']}<br/>{cls.COMPANY_INFO['city']}", normal_style))
        story.append(Paragraph(f"Phone: {cls.COMPANY_INFO['phone']} | Email: {cls.COMPANY_INFO['email']}", normal_style))
        story.append(Spacer(1, 20))
        
        # Add horizontal line
        story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
        story.append(Spacer(1, 20))
        
        # Invoice title and details
        story.append(Paragraph("INVOICE", title_style))
        
        # Invoice info table
        invoice_info_data = [
            ["Invoice Number:", invoice.invoice_number],
            ["Invoice Date:", invoice.invoice_date.strftime("%B %d, %Y")],
            ["Due Date:", invoice.due_date.strftime("%B %d, %Y")],
            ["Status:", invoice.status.value.title()],
        ]
        
        if invoice.paid_date:
            invoice_info_data.append(["Paid Date:", invoice.paid_date.strftime("%B %d, %Y")])
        
        invoice_info_table = Table(invoice_info_data, colWidths=[2*inch, 2*inch])
        invoice_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(invoice_info_table)
        story.append(Spacer(1, 20))
        
        # Bill to section
        story.append(Paragraph("Bill To:", header_style))
        bill_to_text = f"{user.full_name}<br/>{user.email}"
        story.append(Paragraph(bill_to_text, normal_style))
        story.append(Spacer(1, 20))
        
        # Billing period
        if invoice.period_start and invoice.period_end:
            period_text = f"Billing Period: {invoice.period_start.strftime('%B %d, %Y')} - {invoice.period_end.strftime('%B %d, %Y')}"
            story.append(Paragraph(period_text, normal_style))
            story.append(Spacer(1, 15))
        
        # Invoice items table
        story.append(Paragraph("Invoice Details:", header_style))
        
        # Table headers
        items_data = [["Description", "Quantity", "Unit Price", "Amount"]]
        
        # Add invoice items
        for item in invoice_items:
            items_data.append([
                item.description,
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.amount:.2f}"
            ])
        
        # Add subtotal, tax, and total rows
        items_data.extend([
            ["", "", "", ""],  # Empty row for spacing
            ["", "", "Subtotal:", f"${invoice.amount_subtotal:.2f}"],
            ["", "", "Tax:", f"${invoice.amount_tax:.2f}"],
            ["", "", "Total:", f"${invoice.amount_total:.2f}"]
        ])
        
        items_table = Table(items_data, colWidths=[3.5*inch, 1*inch, 1.25*inch, 1.25*inch])
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Summary rows (last 4 rows)
            ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, -3), (-1, -1), 11),
            ('LINEABOVE', (2, -3), (-1, -3), 1, colors.black),
            
            # Total row
            ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTSIZE', (2, -1), (-1, -1), 12),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -4), 1, colors.HexColor('#e5e7eb')),
            ('LINEBELOW', (0, -4), (-1, -4), 1, colors.HexColor('#e5e7eb')),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Payment status
        if invoice.amount_total == 0:
            payment_text = "This invoice is for $0.00 and has been automatically marked as paid."
            story.append(Paragraph(payment_text, normal_style))
        elif invoice.paid_date:
            payment_text = f"Thank you! This invoice was paid on {invoice.paid_date.strftime('%B %d, %Y')}."
            story.append(Paragraph(payment_text, normal_style))
        else:
            payment_text = f"Payment is due by {invoice.due_date.strftime('%B %d, %Y')}. Please contact us for payment instructions."
            story.append(Paragraph(payment_text, normal_style))
        
        story.append(Spacer(1, 20))
        
        # Footer
        story.append(HRFlowable(width="100%", thickness=1, lineCap='round', color=colors.grey))
        story.append(Spacer(1, 10))
        
        footer_text = f"Thank you for using {cls.COMPANY_INFO['name']}!<br/>"
        footer_text += f"Questions? Contact us at {cls.COMPANY_INFO['email']} or visit {cls.COMPANY_INFO['website']}"
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER
        )
        
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    @classmethod
    def save_invoice_pdf(
        cls,
        invoice: Invoice,
        user: User,
        invoice_items: list[InvoiceItem],
        storage_dir: str = "invoices"
    ) -> str:
        """Generate and save invoice PDF, return file path"""
        
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        
        # Generate filename
        filename = f"invoice_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(storage_dir, filename)
        
        # Generate PDF
        cls.generate_invoice_pdf(invoice, user, invoice_items, file_path)
        
        return file_path
