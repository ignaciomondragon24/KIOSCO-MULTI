"""
PDF Generation Helpers for CHE GOLOSO
"""
import io
from decimal import Decimal
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def format_currency(value):
    """Format value as Argentine peso."""
    if value is None:
        return '$0'
    
    # Convert to Decimal if needed
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    
    # Format with thousands separator only (no decimals)
    formatted = '{:,.0f}'.format(value)
    # Replace for Argentine format (. for thousands)
    formatted = formatted.replace(',', '.')
    return f'${formatted}'


def generate_receipt_pdf(transaction):
    """Generate PDF receipt for a POS transaction."""
    buffer = io.BytesIO()
    
    # Create document - 80mm thermal paper width
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(80*mm, 297*mm),
        rightMargin=5*mm,
        leftMargin=5*mm,
        topMargin=5*mm,
        bottomMargin=5*mm
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_LEFT
    )
    
    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER
    )
    
    right_style = ParagraphStyle(
        'Right',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_RIGHT
    )
    
    elements = []
    
    # Header
    from company.models import Company
    company = Company.get_company()
    
    elements.append(Paragraph(company.name, title_style))
    if company.address:
        elements.append(Paragraph(company.address, center_style))
    if company.cuit:
        elements.append(Paragraph(f'CUIT: {company.cuit}', center_style))
    
    elements.append(Spacer(1, 5*mm))
    
    # Receipt info
    elements.append(Paragraph(f'<b>Ticket:</b> {transaction.ticket_number}', normal_style))
    elements.append(Paragraph(
        f'<b>Fecha:</b> {transaction.created_at.strftime("%d/%m/%Y %H:%M")}',
        normal_style
    ))
    elements.append(Paragraph(f'<b>Caja:</b> {transaction.session.shift.cash_register.name}', normal_style))
    elements.append(Paragraph(f'<b>Cajero:</b> {transaction.session.cashier.get_full_name()}', normal_style))
    
    elements.append(Spacer(1, 5*mm))
    
    # Items table
    items_data = [['Producto', 'Cant', 'P.Unit', 'Total']]
    
    for item in transaction.items.all():
        items_data.append([
            item.product_name[:20],  # Truncate long names
            str(item.quantity),
            format_currency(item.unit_price),
            format_currency(item.subtotal)
        ])
    
    items_table = Table(items_data, colWidths=[30*mm, 10*mm, 15*mm, 15*mm])
    items_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 3*mm))
    
    # Totals
    elements.append(Paragraph(f'<b>Subtotal:</b> {format_currency(transaction.subtotal)}', right_style))
    
    if transaction.discount_amount > 0:
        elements.append(Paragraph(
            f'<b>Descuento:</b> -{format_currency(transaction.discount_amount)}',
            right_style
        ))
    
    elements.append(Spacer(1, 2*mm))
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_RIGHT,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(f'TOTAL: {format_currency(transaction.total)}', total_style))
    
    elements.append(Spacer(1, 3*mm))
    
    # Payments
    elements.append(Paragraph('<b>Forma de Pago:</b>', normal_style))
    for payment in transaction.payments.all():
        elements.append(Paragraph(
            f'{payment.payment_method.name}: {format_currency(payment.amount)}',
            normal_style
        ))
    
    if transaction.change_amount > 0:
        elements.append(Paragraph(
            f'<b>Vuelto:</b> {format_currency(transaction.change_amount)}',
            normal_style
        ))
    
    elements.append(Spacer(1, 5*mm))
    
    # Footer
    if company.receipt_footer:
        elements.append(Paragraph(company.receipt_footer, center_style))
    
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph('¡Gracias por su compra!', center_style))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    return buffer


def generate_report_pdf(title, data, columns, totals=None):
    """Generate a generic report PDF."""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    elements.append(Paragraph(title, title_style))
    
    # Date
    from datetime import datetime
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
        spaceAfter=20
    )
    elements.append(Paragraph(
        f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
        date_style
    ))
    
    # Data table
    if data:
        table_data = [columns] + data
        
        col_width = (doc.width) / len(columns)
        table = Table(table_data, colWidths=[col_width] * len(columns))
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
    
    # Totals
    if totals:
        elements.append(Spacer(1, 20))
        for label, value in totals.items():
            elements.append(Paragraph(
                f'<b>{label}:</b> {value}',
                styles['Normal']
            ))
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer


def pdf_response(buffer, filename):
    """Create HTTP response for PDF download."""
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
