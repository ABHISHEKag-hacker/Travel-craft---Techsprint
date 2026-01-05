"""
PDF Generator
==============
Generates beautiful PDF itineraries for travel plans.
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def format_currency(amount):
    """Format currency with Rs. prefix (PDF-safe)"""
    return f"Rs. {amount:,.0f}"


def generate_pdf(plan: dict) -> io.BytesIO:
    """Generate a beautiful PDF itinerary"""
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        spaceAfter=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2C4A52'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#537A82'),
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        spaceBefore=25,
        spaceAfter=12,
        textColor=colors.HexColor('#2C4A52'),
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        fontName='Helvetica'
    )
    
    # Build PDF content
    elements = []
    
    # ========== TITLE SECTION ==========
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("TRAVEL ITINERARY", title_style))
    
    city_name = plan.get('city', 'Unknown').upper()
    num_days = plan.get('num_days', 0)
    elements.append(Paragraph(f"{city_name} - {num_days} Days Adventure", subtitle_style))
    
    # Decorative line
    elements.append(HRFlowable(width="60%", thickness=3, color=colors.HexColor('#C17F59'), 
                               spaceAfter=20, hAlign='CENTER'))
    elements.append(Spacer(1, 10))
    
    # ========== TRIP OVERVIEW ==========
    budget = plan.get('budget', 0)
    total_cost = plan.get('total_cost', 0)
    travel_cost = plan.get('travel_cost', 0)
    hotel_cost = plan.get('hotel_cost', 0)
    grand_total = total_cost + travel_cost + hotel_cost
    remaining = budget - grand_total
    utilization = plan.get('utilization', 0)
    
    overview_data = [
        ['TRIP OVERVIEW', ''],
        ['Destination', city_name],
        ['Duration', f"{num_days} Days"],
        ['Travelers', f"{plan.get('adults', 2)} Adults, {plan.get('children', 0)} Children"],
        ['Budget', format_currency(budget)],
        ['Activities Cost', format_currency(total_cost)],
    ]
    
    # Add travel cost if present
    if travel_cost > 0:
        overview_data.append(['Travel Cost', format_currency(travel_cost)])
    
    # Add hotel cost if present
    if hotel_cost > 0:
        overview_data.append(['Hotel Cost', format_currency(hotel_cost)])
    
    overview_data.extend([
        ['Grand Total', format_currency(grand_total)],
        ['Remaining', format_currency(remaining)],
        ['Budget Utilization', f"{utilization}%"],
        ['Preferences', ', '.join(plan.get('preferences', [])).title()]
    ])
    
    overview_table = Table(overview_data, colWidths=[3*inch, 4*inch])
    overview_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C4A52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        # Label column
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    
    elements.append(overview_table)
    elements.append(Spacer(1, 25))
    
    # ========== TRIP SUMMARY ==========
    summary = plan.get('summary', '')
    if summary:
        elements.append(Paragraph("Trip Summary", heading_style))
        
        summary_box_style = ParagraphStyle(
            'SummaryBox',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Oblique',
            textColor=colors.HexColor('#495057'),
            leftIndent=20,
            rightIndent=20,
            spaceBefore=10,
            spaceAfter=10,
            leading=16
        )
        elements.append(Paragraph(summary.replace('"', '').strip(), summary_box_style))
        elements.append(Spacer(1, 15))
    
    # ========== DAILY ITINERARY ==========
    elements.append(Paragraph("Daily Itinerary", heading_style))
    elements.append(Spacer(1, 10))
    
    for day in plan.get('days', []):
        day_num = day.get('day_number', 0)
        day_cost = day.get('total_cost', 0)
        
        # Day Header
        day_header_data = [[f"DAY {day_num}", format_currency(day_cost)]]
        day_header_table = Table(day_header_data, colWidths=[5.5*inch, 1.5*inch])
        day_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#537A82')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 14),
            ('FONTSIZE', (1, 0), (1, 0), 12),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROUNDEDCORNERS', [5, 5, 0, 0]),
        ]))
        elements.append(day_header_table)
        
        # Activities Table
        activity_data = [['Time', 'Activity', 'Hours', 'Cost']]
        
        for activity in day.get('activities', []):
            time_slot = activity.get('time_slot', 'morning').capitalize()
            name = activity.get('name', 'Activity')
            desc = activity.get('description', '')
            if len(desc) > 60:
                desc = desc[:60] + "..."
            
            activity_text = f"<b>{name}</b><br/><font size='9' color='#6c757d'>{desc}</font>"
            
            activity_data.append([
                time_slot,
                Paragraph(activity_text, styles['Normal']),
                f"{activity.get('duration_hours', 0)}h",
                format_currency(activity.get('cost', 0))
            ])
        
        activity_table = Table(activity_data, colWidths=[1*inch, 4*inch, 0.8*inch, 1.2*inch])
        activity_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#495057')),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(activity_table)
        elements.append(Spacer(1, 20))
    
    # ========== COST BREAKDOWN ==========
    elements.append(Paragraph("Cost Breakdown", heading_style))
    elements.append(Spacer(1, 10))
    
    cost_data = [['Item', 'Amount']]
    
    # Add travel if present
    if travel_cost > 0:
        travel_details = plan.get('travel_details', 'Travel')
        cost_data.append(['Travel: ' + travel_details, format_currency(travel_cost)])
    
    # Add hotel if present
    if hotel_cost > 0:
        hotel_details = plan.get('hotel_details', 'Hotel')
        cost_data.append(['Hotel: ' + hotel_details, format_currency(hotel_cost)])
    
    # Add daily costs
    for day in plan.get('days', []):
        cost_data.append([f"Day {day.get('day_number', 0)} Activities", format_currency(day.get('total_cost', 0))])
    
    # Totals
    cost_data.append(['', ''])
    cost_data.append(['GRAND TOTAL', format_currency(grand_total)])
    cost_data.append(['BUDGET', format_currency(budget)])
    cost_data.append(['REMAINING', format_currency(remaining)])
    
    cost_table = Table(cost_data, colWidths=[4.5*inch, 2.5*inch])
    cost_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        # Totals section
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#d4edda')),
        ('FONTSIZE', (0, -3), (-1, -1), 11),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -4), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    elements.append(cost_table)
    
    # ========== FOOTER ==========
    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    elements.append(Spacer(1, 15))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6c757d'),
        fontName='Helvetica'
    )
    
    generation_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    elements.append(Paragraph(
        f"Generated by AI Travel Planner | {generation_date}",
        footer_style
    ))
    elements.append(Paragraph(
        "Powered by DeepSeek AI",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer
