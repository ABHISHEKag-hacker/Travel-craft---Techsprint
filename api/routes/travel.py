"""
Travel Routes
==============
API routes for travel planning functionality.
"""

from flask import Blueprint, request, jsonify, make_response
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.travel_planner import TravelPlannerAgent, UserInput
from api.utils.cost_calculator import estimate_travel_cost, calculate_hotel_cost, get_activity_emoji
from api.utils.pdf_generator import generate_pdf

travel_bp = Blueprint('travel', __name__)


@travel_bp.route('/plan', methods=['POST'])
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
        
        # Travel and hotel inputs
        origin_city = data.get('origin_city', '')
        include_hotel = data.get('include_hotel', False)
        hotel_rating = int(data.get('hotel_rating', 3))
        room_type = data.get('room_type', 'ac')
        
        # Calculate travel cost
        travel_cost = 0
        travel_details = ""
        if origin_city and origin_city.strip():
            travel_cost_per_person = estimate_travel_cost(origin_city, city)
            travel_cost = (travel_cost_per_person * adults) + (travel_cost_per_person * 0.5 * children)
            travel_details = f"{origin_city} → {city} • {adults} adults, {children} children (round trip)"
        
        # Calculate hotel cost
        hotel_cost = 0
        hotel_details = ""
        if include_hotel:
            rooms_needed = max(1, (adults + 1) // 2)
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
            # Still create a minimal plan with reduced costs
            activity_budget = budget * 0.2  # Only 20% for basic activities
        elif fixed_costs > budget * 0.8:
            # Warning if fixed costs use more than 80% of budget
            budget_warning = f"⚠️ Travel and hotel costs use {(fixed_costs/budget*100):.0f}% of your budget. Limited activities will be suggested."
            activity_budget = budget - fixed_costs
        else:
            activity_budget = budget - fixed_costs
        
        # Ensure minimum activity budget
        if activity_budget < 0:
            activity_budget = 500  # Minimum budget for activities
        
        # Create user input and generate plan
        user_input = UserInput(
            budget=activity_budget,
            num_days=num_days,
            city=city,
            activity_preferences=preferences
        )
        
        agent = TravelPlannerAgent()
        travel_plan = agent.create_travel_plan(user_input)
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
        
        # Build response
        plan_data = {
            'city': travel_plan.city,
            'budget': budget,
            'num_days': travel_plan.num_days,
            'adults': adults,
            'children': children,
            'total_travelers': total_travelers,
            'preferences': travel_plan.preferences,
            'total_cost': travel_plan.total_cost,
            'travel_cost': travel_cost,
            'travel_details': travel_details,
            'hotel_cost': hotel_cost,
            'hotel_details': hotel_details,
            'remaining': remaining,
            'utilization': min(utilization, 100),  # Cap at 100%
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


@travel_bp.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF of the travel itinerary"""
    try:
        data = request.get_json()
        plan = data.get('plan')
        
        if not plan:
            return jsonify({'success': False, 'error': 'No plan data provided'}), 400
        
        pdf_buffer = generate_pdf(plan)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Travel_Itinerary_{plan["city"]}_{plan["num_days"]}days.pdf'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
