"""
Travel Planner Agent - Web Interface
=====================================
A beautiful Flask web application for the AI Travel Planner.
"""

from flask import Flask, render_template, request, jsonify, send_file, make_response
import json
import threading
import time
import io
from datetime import datetime

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Import the Travel Planner Agent components
from importlib.util import spec_from_file_location, module_from_spec
import sys
import os

# Load the travel planner module
spec = spec_from_file_location("travel_planner", "Travel Planner Agent.py")
travel_planner = module_from_spec(spec)
spec.loader.exec_module(travel_planner)

app = Flask(__name__)
app.secret_key = 'travel-planner-secret-key-2024'

# Store planning results
planning_results = {}


@app.route('/')
def index():
    """Render the main page with the input form"""
    return render_template('index.html')


@app.route('/plan', methods=['POST'])
def create_plan():
    """Create a travel plan based on user input"""
    try:
        data = request.get_json()
        
        # Extract inputs
        budget = float(data.get('budget', 1000))
        num_days = int(data.get('days', 3))
        city = data.get('city', 'Paris')
        preferences = data.get('preferences', ['sightseeing', 'food', 'cultural'])
        
        # Create user input object
        user_input = travel_planner.UserInput(
            budget=budget,
            num_days=num_days,
            city=city,
            activity_preferences=preferences
        )
        
        # Create agent and generate plan
        agent = travel_planner.TravelPlannerAgent()
        travel_plan = agent.create_travel_plan(user_input)
        
        # Generate summary
        summary = agent.generate_itinerary_summary(travel_plan)
        
        # Convert plan to JSON-serializable format
        plan_data = {
            'city': travel_plan.city,
            'budget': travel_plan.budget,
            'num_days': travel_plan.num_days,
            'preferences': travel_plan.preferences,
            'total_cost': travel_plan.total_cost,
            'remaining': travel_plan.budget - travel_plan.total_cost,
            'utilization': round((travel_plan.total_cost / travel_plan.budget) * 100, 1),
            'summary': summary if summary else "Enjoy your amazing trip!",
            'days': []
        }
        
        for day in travel_plan.days:
            day_data = {
                'day_number': day.day_number,
                'total_cost': day.total_cost,
                'total_hours': day.total_hours,
                'activities': []
            }
            
            # Sort activities by time slot
            time_order = {"morning": 0, "afternoon": 1, "evening": 2}
            sorted_activities = sorted(day.activities, key=lambda x: time_order.get(x.time_slot, 1))
            
            for activity in sorted_activities:
                activity_data = {
                    'name': activity.name,
                    'description': activity.description,
                    'duration_hours': activity.duration_hours,
                    'cost': activity.cost,
                    'activity_type': activity.activity_type,
                    'time_slot': activity.time_slot,
                    'emoji': get_activity_emoji(activity.activity_type)
                }
                day_data['activities'].append(activity_data)
            
            plan_data['days'].append(day_data)
        
        return jsonify({'success': True, 'plan': plan_data})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF of the travel itinerary"""
    try:
        data = request.get_json()
        plan = data.get('plan')
        
        if not plan:
            return jsonify({'success': False, 'error': 'No plan data provided'}), 400
        
        # Generate PDF
        pdf_buffer = generate_pdf(plan)
        
        # Create response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Travel_Itinerary_{plan["city"]}_{plan["num_days"]}days.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_pdf(plan):
    """Generate a beautiful PDF itinerary"""
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4f46e5')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#64748b')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#1e293b')
    )
    
    day_heading_style = ParagraphStyle(
        'DayHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.white,
        backColor=colors.HexColor('#6366f1'),
        borderPadding=10
    )
    
    activity_name_style = ParagraphStyle(
        'ActivityName',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e293b')
    )
    
    activity_desc_style = ParagraphStyle(
        'ActivityDesc',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=5
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6
    )
    
    # Build PDF content
    elements = []
    
    # Title
    elements.append(Paragraph("Travel Itinerary", title_style))
    elements.append(Paragraph(f"{plan['city']} - {plan['num_days']} Days Adventure", subtitle_style))
    
    # Horizontal line
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 20))
    
    # Trip Overview Table
    overview_data = [
        ['Trip Overview', ''],
        ['Destination', plan['city']],
        ['Duration', f"{plan['num_days']} Days"],
        ['Budget', f"₹{plan['budget']:,.0f}"],
        ['Total Cost', f"₹{plan['total_cost']:,.0f}"],
        ['Remaining', f"₹{plan['remaining']:,.0f}"],
        ['Budget Utilization', f"{plan['utilization']}%"],
        ['Preferences', ', '.join(plan['preferences']).title()]
    ]
    
    overview_table = Table(overview_data, colWidths=[3*inch, 4*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f1f5f9')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(overview_table)
    elements.append(Spacer(1, 30))
    
    # Summary
    if plan.get('summary'):
        elements.append(Paragraph("Trip Summary", heading_style))
        summary_text = plan['summary'].replace('"', '').strip()
        elements.append(Paragraph(f"<i>{summary_text}</i>", normal_style))
        elements.append(Spacer(1, 20))
    
    # Daily Itinerary
    elements.append(Paragraph("Daily Itinerary", heading_style))
    elements.append(Spacer(1, 10))
    
    for day in plan['days']:
        # Day Header
        day_header_data = [[f"Day {day['day_number']}", f"₹{day['total_cost']:,.0f}"]]
        day_header_table = Table(day_header_data, colWidths=[5.5*inch, 1.5*inch])
        day_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 14),
            ('FONTSIZE', (1, 0), (1, 0), 12),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(day_header_table)
        
        # Activities Table
        activity_data = [['Time', 'Activity', 'Duration', 'Cost']]
        
        for activity in day['activities']:
            activity_data.append([
                activity['time_slot'].capitalize(),
                f"{activity['name']}\n{activity['description'][:80]}..." if len(activity['description']) > 80 else f"{activity['name']}\n{activity['description']}",
                f"{activity['duration_hours']}h",
                f"₹{activity['cost']:,.0f}"
            ])
        
        activity_table = Table(activity_data, colWidths=[1*inch, 4*inch, 0.8*inch, 1.2*inch])
        activity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ]))
        elements.append(activity_table)
        elements.append(Spacer(1, 15))
    
    # Cost Breakdown
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Cost Breakdown", heading_style))
    
    cost_data = [['Day', 'Cost']]
    for day in plan['days']:
        cost_data.append([f"Day {day['day_number']}", f"₹{day['total_cost']:,.0f}"])
    cost_data.append(['', ''])
    cost_data.append(['Total', f"₹{plan['total_cost']:,.0f}"])
    cost_data.append(['Budget', f"₹{plan['budget']:,.0f}"])
    cost_data.append(['Remaining', f"₹{plan['remaining']:,.0f}"])
    
    cost_table = Table(cost_data, colWidths=[3*inch, 2*inch])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(cost_table)
    
    # Footer
    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 10))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#94a3b8')
    )
    elements.append(Paragraph(
        f"Generated by AI Travel Planner | Powered by Llama AI | {datetime.now().strftime('%B %d, %Y')}",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def get_activity_emoji(activity_type):
    """Get emoji for activity type"""
    emoji_map = {
        "sightseeing": "🏛️",
        "adventure": "🎢",
        "cultural": "🎭",
        "food": "🍽️",
        "relaxation": "🧘",
        "shopping": "🛍️",
        "nightlife": "🌙"
    }
    return emoji_map.get(activity_type, "📍")


if __name__ == '__main__':
    # Create templates folder if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("\n" + "="*60)
    print("🌍 TRAVEL PLANNER - WEB INTERFACE 🌍".center(60))
    print("="*60)
    print("\n🚀 Starting server at: http://localhost:5000")
    print("📝 Open this URL in your browser to use the Travel Planner")
    print("\nPress CTRL+C to stop the server\n")
    
    app.run(debug=True, port=5000)
