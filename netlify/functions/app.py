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

# For Netlify Functions - get the directory where this script is located
FUNCTION_DIR = os.path.dirname(os.path.abspath(__file__))

# Load the travel planner module from the same directory
spec = spec_from_file_location("travel_planner", os.path.join(FUNCTION_DIR, "Travel Planner Agent.py"))
travel_planner = module_from_spec(spec)
spec.loader.exec_module(travel_planner)

# Create Flask app with correct template folder for Netlify Functions
app = Flask(__name__, template_folder=os.path.join(FUNCTION_DIR, 'templates'))
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
        
        # Travelers
        adults = int(data.get('adults', 2))
        children = int(data.get('children', 0))
        total_travelers = adults + children
        
        # New inputs for travel and hotel
        origin_city = data.get('origin_city', '')
        include_hotel = data.get('include_hotel', False)
        hotel_rating = int(data.get('hotel_rating', 3))
        room_type = data.get('room_type', 'ac')
        
        # Calculate travel cost (estimated based on origin-destination)
        # Multiply by total travelers
        travel_cost = 0
        travel_details = ""
        if origin_city and origin_city.strip():
            travel_cost_per_person = estimate_travel_cost(origin_city, city)
            # Children travel at 50% cost
            travel_cost = (travel_cost_per_person * adults) + (travel_cost_per_person * 0.5 * children)
            travel_details = f"{origin_city} → {city} • {adults} adults, {children} children (round trip)"
        
        # Calculate hotel cost
        # Estimate rooms needed: 1 room per 2 adults, children share
        hotel_cost = 0
        hotel_details = ""
        if include_hotel:
            rooms_needed = max(1, (adults + 1) // 2)  # 1 room per 2 adults
            hotel_cost_per_room = calculate_hotel_cost(hotel_rating, room_type, num_days, city)
            hotel_cost = hotel_cost_per_room * rooms_needed
            rating_stars = "⭐" * hotel_rating
            ac_text = "AC" if room_type == 'ac' else "Non-AC"
            hotel_details = f"{rating_stars} {ac_text} • {rooms_needed} room(s) × {num_days} nights"
        
        # Check if travel + hotel already exceeds budget
        fixed_costs = travel_cost + hotel_cost
        budget_warning = None
        budget_exceeded = False
        
        if fixed_costs >= budget:
            budget_exceeded = True
            budget_warning = f"⚠️ Your travel (Rs. {travel_cost:,.0f}) and hotel (Rs. {hotel_cost:,.0f}) costs alone exceed your budget of Rs. {budget:,.0f}. Please increase your budget or reduce hotel rating/travelers."
            activity_budget = budget * 0.2  # Only 20% for basic activities
        elif fixed_costs > budget * 0.8:
            budget_warning = f"⚠️ Travel and hotel costs use {(fixed_costs/budget*100):.0f}% of your budget. Limited activities will be suggested."
            activity_budget = budget - fixed_costs
        else:
            activity_budget = budget - fixed_costs
        
        # Ensure minimum activity budget
        if activity_budget < 0:
            activity_budget = 500
        
        # Create user input object with adjusted budget
        user_input = travel_planner.UserInput(
            budget=activity_budget,
            num_days=num_days,
            city=city,
            activity_preferences=preferences
        )
        
        # Create agent and generate plan
        agent = travel_planner.TravelPlannerAgent()
        travel_plan = agent.create_travel_plan(user_input)
        
        # Generate summary
        summary = agent.generate_itinerary_summary(travel_plan)
        
        # Calculate grand total
        grand_total = travel_plan.total_cost + travel_cost + hotel_cost
        remaining = budget - grand_total
        utilization = round((grand_total / budget) * 100, 1)
        
        # Add warning if total exceeds budget
        if grand_total > budget and not budget_warning:
            over_budget = grand_total - budget
            budget_warning = f"⚠️ Total cost exceeds budget by Rs. {over_budget:,.0f}. Consider reducing hotel rating or travel distance."
            budget_exceeded = True
        
        # Convert plan to JSON-serializable format
        plan_data = {
            'city': travel_plan.city,
            'budget': budget,  # Original budget
            'num_days': travel_plan.num_days,
            'adults': adults,
            'children': children,
            'total_travelers': total_travelers,
            'preferences': travel_plan.preferences,
            'total_cost': travel_plan.total_cost,  # Activity cost only
            'travel_cost': travel_cost,
            'travel_details': travel_details,
            'hotel_cost': hotel_cost,
            'hotel_details': hotel_details,
            'remaining': remaining,
            'utilization': min(utilization, 100),
            'budget_warning': budget_warning,
            'budget_exceeded': budget_exceeded,
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


def estimate_travel_cost(origin: str, destination: str) -> float:
    """
    Estimate travel cost based on origin and destination cities in India.
    Uses approximate pricing for train/bus travel.
    """
    # Common Indian city pairs with approximate distances (in km)
    city_distances = {
        # Major metro distances from each other
        ('mumbai', 'delhi'): 1400,
        ('mumbai', 'bangalore'): 980,
        ('mumbai', 'chennai'): 1330,
        ('mumbai', 'kolkata'): 1870,
        ('mumbai', 'hyderabad'): 710,
        ('mumbai', 'pune'): 150,
        ('mumbai', 'goa'): 590,
        ('mumbai', 'jaipur'): 1150,
        ('delhi', 'bangalore'): 2150,
        ('delhi', 'chennai'): 2180,
        ('delhi', 'kolkata'): 1530,
        ('delhi', 'hyderabad'): 1550,
        ('delhi', 'jaipur'): 280,
        ('delhi', 'agra'): 230,
        ('delhi', 'manali'): 530,
        ('delhi', 'shimla'): 350,
        ('bangalore', 'chennai'): 350,
        ('bangalore', 'hyderabad'): 570,
        ('bangalore', 'goa'): 560,
        ('bangalore', 'mysore'): 150,
        ('kolkata', 'chennai'): 1670,
        ('chennai', 'hyderabad'): 630,
    }
    
    origin_lower = origin.lower().strip()
    dest_lower = destination.lower().strip()
    
    # Check if we have this route
    distance = None
    for (city1, city2), dist in city_distances.items():
        if (city1 in origin_lower or origin_lower in city1) and \
           (city2 in dest_lower or dest_lower in city2):
            distance = dist
            break
        if (city2 in origin_lower or origin_lower in city2) and \
           (city1 in dest_lower or dest_lower in city1):
            distance = dist
            break
    
    # If no known route, estimate based on assumption
    if distance is None:
        distance = 800  # Default ~800km
    
    # Price per km (mix of train and bus rates in India)
    # Sleeper class train: ~₹1.5/km, AC train: ~₹3/km, Bus: ~₹1.5-2/km
    price_per_km = 2.5  # Average
    
    # Round trip
    travel_cost = distance * price_per_km * 2
    
    # Add some buffer for local transport
    travel_cost += 500
    
    return round(travel_cost, 0)


def calculate_hotel_cost(rating: int, room_type: str, num_days: int, city: str) -> float:
    """
    Calculate estimated hotel cost based on rating, room type, and city.
    """
    # Base prices per night in INR based on star rating
    base_prices = {
        2: 800,   # Budget
        3: 1500,  # Standard
        4: 3500,  # Premium
        5: 8000   # Luxury
    }
    
    base_price = base_prices.get(rating, 1500)
    
    # AC premium (30% more for AC)
    if room_type == 'ac':
        base_price *= 1.3
    
    # City-based multiplier (some cities are more expensive)
    expensive_cities = ['mumbai', 'delhi', 'bangalore', 'goa', 'chennai', 'hyderabad']
    moderate_cities = ['pune', 'jaipur', 'kolkata', 'ahmedabad']
    
    city_lower = city.lower()
    if any(c in city_lower for c in expensive_cities):
        base_price *= 1.4
    elif any(c in city_lower for c in moderate_cities):
        base_price *= 1.2
    
    # Calculate total for all nights
    total_hotel_cost = base_price * num_days
    
    return round(total_hotel_cost, 0)


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
    
    def format_currency(amount):
        """Format currency with Rs. prefix (PDF-safe)"""
        return f"Rs. {amount:,.0f}"
    
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
    
    # Title Section
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("TRAVEL ITINERARY", title_style))
    
    city_name = plan.get('city', 'Unknown').upper()
    num_days = plan.get('num_days', 0)
    elements.append(Paragraph(f"{city_name} - {num_days} Days Adventure", subtitle_style))
    
    # Decorative line
    elements.append(HRFlowable(width="60%", thickness=3, color=colors.HexColor('#C17F59'), 
                               spaceAfter=20, hAlign='CENTER'))
    elements.append(Spacer(1, 10))
    
    # Calculate totals
    budget = plan.get('budget', 0)
    total_cost = plan.get('total_cost', 0)
    travel_cost = plan.get('travel_cost', 0)
    hotel_cost = plan.get('hotel_cost', 0)
    grand_total = total_cost + travel_cost + hotel_cost
    remaining = budget - grand_total
    utilization = plan.get('utilization', 0)
    
    # Trip Overview Table
    overview_data = [
        ['TRIP OVERVIEW', ''],
        ['Destination', city_name],
        ['Duration', f"{num_days} Days"],
        ['Travelers', f"{plan.get('adults', 2)} Adults, {plan.get('children', 0)} Children"],
        ['Budget', format_currency(budget)],
        ['Activities Cost', format_currency(total_cost)],
    ]
    
    if travel_cost > 0:
        overview_data.append(['Travel Cost', format_currency(travel_cost)])
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C4A52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f8f9fa')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(overview_table)
    elements.append(Spacer(1, 25))
    
    # Summary
    if plan.get('summary'):
        elements.append(Paragraph("Trip Summary", heading_style))
        summary_style = ParagraphStyle(
            'SummaryBox', parent=styles['Normal'], fontSize=11,
            fontName='Helvetica-Oblique', textColor=colors.HexColor('#495057'),
            leftIndent=20, rightIndent=20, spaceBefore=10, spaceAfter=10, leading=16
        )
        elements.append(Paragraph(plan['summary'].replace('"', '').strip(), summary_style))
        elements.append(Spacer(1, 15))
    
    # Daily Itinerary
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
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#495057')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ]))
        elements.append(activity_table)
        elements.append(Spacer(1, 20))
    
    # Cost Breakdown
    elements.append(Paragraph("Cost Breakdown", heading_style))
    elements.append(Spacer(1, 10))
    
    cost_data = [['Item', 'Amount']]
    
    if travel_cost > 0:
        cost_data.append(['Travel: ' + plan.get('travel_details', 'Travel'), format_currency(travel_cost)])
    if hotel_cost > 0:
        cost_data.append(['Hotel: ' + plan.get('hotel_details', 'Hotel'), format_currency(hotel_cost)])
    
    for day in plan.get('days', []):
        cost_data.append([f"Day {day.get('day_number', 0)} Activities", format_currency(day.get('total_cost', 0))])
    
    cost_data.append(['', ''])
    cost_data.append(['GRAND TOTAL', format_currency(grand_total)])
    cost_data.append(['BUDGET', format_currency(budget)])
    cost_data.append(['REMAINING', format_currency(remaining)])
    
    cost_table = Table(cost_data, colWidths=[4.5*inch, 2.5*inch])
    cost_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#d4edda')),
        ('FONTSIZE', (0, -3), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    elements.append(cost_table)
    
    # Footer
    elements.append(Spacer(1, 40))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dee2e6')))
    elements.append(Spacer(1, 15))
    
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER,
        textColor=colors.HexColor('#6c757d'), fontName='Helvetica'
    )
    
    generation_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    elements.append(Paragraph(f"Generated by AI Travel Planner | {generation_date}", footer_style))
    elements.append(Paragraph("Powered by DeepSeek AI", footer_style))
    
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


# Netlify Functions Handler
# This is the handler that Netlify will call
try:
    import serverless_wsgi
    
    def handler(event, context):
        """
        Netlify Functions handler that wraps the Flask app
        using serverless-wsgi for AWS Lambda compatibility.
        """
        return serverless_wsgi.handle_request(app, event, context)
        
except ImportError:
    # Fallback for local development without serverless-wsgi
    def handler(event, context):
        return {
            'statusCode': 500,
            'body': 'serverless-wsgi not installed'
        }

if __name__ == '__main__':
    # Local development mode
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("\n" + "="*60)
    print("🌍 TRAVEL PLANNER - WEB INTERFACE 🌍".center(60))
    print("="*60)
    print("\n🚀 Starting server at: http://localhost:5000")
    print("📝 Open this URL in your browser to use the Travel Planner")
    print("\nPress CTRL+C to stop the server\n")
    
    app.run(debug=True, port=5000)