"""
Travel Planner Agent
=====================
An agentic AI system that creates travel itineraries using LLM models.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

try:
    from openai import OpenAI
except ImportError:
    print("Please install openai: pip install openai")
    exit(1)

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    OPENROUTER_API_KEY, 
    OPENROUTER_BASE_URL, 
    DEFAULT_MODEL,
    MAX_REPLANNING_ATTEMPTS,
    HOURS_PER_DAY,
    BUDGET_UTILIZATION_TARGET,
    MIN_DAILY_SPEND_RATIO,
    MAX_TOKENS
)


# ============================================================================
# Data Models
# ============================================================================

class ActivityType(Enum):
    SIGHTSEEING = "sightseeing"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    FOOD = "food"
    RELAXATION = "relaxation"
    SHOPPING = "shopping"
    NIGHTLIFE = "nightlife"


@dataclass
class Activity:
    """Represents a single activity in the itinerary"""
    name: str
    description: str
    duration_hours: float
    cost: float
    activity_type: str
    time_slot: str  # morning, afternoon, evening


@dataclass
class DayPlan:
    """Represents a single day's plan"""
    day_number: int
    activities: list[Activity] = field(default_factory=list)
    total_cost: float = 0.0
    total_hours: float = 0.0
    
    def add_activity(self, activity: Activity):
        self.activities.append(activity)
        self.total_cost += activity.cost
        self.total_hours += activity.duration_hours


@dataclass
class TravelPlan:
    """Complete travel plan with all days"""
    city: str
    budget: float
    num_days: int
    preferences: list[str]
    days: list[DayPlan] = field(default_factory=list)
    total_cost: float = 0.0
    
    def calculate_total_cost(self) -> float:
        self.total_cost = sum(day.total_cost for day in self.days)
        return self.total_cost


@dataclass
class UserInput:
    """User input for travel planning"""
    budget: float
    num_days: int
    city: str
    activity_preferences: list[str]


# ============================================================================
# LLM Model Interface (OpenRouter)
# ============================================================================

class LlamaAgent:
    """Interface to interact with LLM models via OpenRouter API"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or DEFAULT_MODEL
        self.conversation_history = []
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        
    def query(self, prompt: str, system_prompt: str = None) -> str:
        """Send a query to the LLM model via OpenRouter"""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=MAX_TOKENS
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error querying LLM model: {e}")
            return None
    
    def extract_json(self, response: str) -> Optional[dict]:
        """Extract JSON from model response"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            
            # Try to find JSON array
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
                
        except json.JSONDecodeError:
            pass
        return None


# ============================================================================
# Travel Planner Agent
# ============================================================================

class TravelPlannerAgent:
    """
    Agentic Travel Planner that uses planning → checking → re-planning loops
    with rule-based constraints for budget and time management.
    """
    
    def __init__(self, model_name: str = None):
        self.llama = LlamaAgent(model_name)
        self.max_replanning_attempts = MAX_REPLANNING_ATTEMPTS
        self.hours_per_day = HOURS_PER_DAY
        self.budget_utilization_target = BUDGET_UTILIZATION_TARGET
        self.min_daily_spend_ratio = MIN_DAILY_SPEND_RATIO
        
    def get_system_prompt(self) -> str:
        """System prompt for the travel planning agent"""
        return """You are a travel planner. Respond ONLY with valid JSON. Create premium activities in Indian Rupees (₹).
JSON format: {"activities": [{"name": "string", "description": "short", "duration_hours": float, "cost": float, "activity_type": "sightseeing|adventure|cultural|food|relaxation|shopping|nightlife", "time_slot": "morning|afternoon|evening"}]}"""
    
    def generate_activities_for_day(
        self, 
        city: str, 
        day_number: int, 
        remaining_budget: float,
        preferences: list[str],
        previous_activities: list[str] = None
    ) -> list[Activity]:
        """Generate activities for a single day using Llama"""
        
        previous_str = ""
        if previous_activities:
            previous_str = f"\nAvoid repeating these activities: {', '.join(previous_activities)}"
        
        # Calculate target daily spend
        target_daily_spend = remaining_budget * self.budget_utilization_target / max(1, (self.hours_per_day // 3))
        if day_number == 1:
            target_daily_spend = remaining_budget * self.budget_utilization_target / 3
        
        prompt = f"""Day {day_number} in {city}. Budget: ₹{target_daily_spend:.0f}. Preferences: {', '.join(preferences)}. {self.hours_per_day}h available.{previous_str}
Generate 3-4 activities. Respond with JSON only: {{"activities": [{{"name": "string", "description": "short", "duration_hours": float, "cost": float, "activity_type": "string", "time_slot": "morning|afternoon|evening"}}]}}"""
        
        response = self.llama.query(prompt, self.get_system_prompt())
        
        if not response:
            return self._get_fallback_activities(city, day_number, remaining_budget)
        
        # Parse the response
        data = self.llama.extract_json(response)
        
        if not data or 'activities' not in data:
            print(f"Warning: Could not parse activities for day {day_number}, using fallback")
            return self._get_fallback_activities(city, day_number, remaining_budget)
        
        activities = []
        for act_data in data['activities']:
            try:
                activity = Activity(
                    name=act_data.get('name', 'Unknown Activity'),
                    description=act_data.get('description', ''),
                    duration_hours=float(act_data.get('duration_hours', 2.0)),
                    cost=float(act_data.get('cost', 0.0)),
                    activity_type=act_data.get('activity_type', 'sightseeing'),
                    time_slot=act_data.get('time_slot', 'morning')
                )
                activities.append(activity)
            except (KeyError, ValueError) as e:
                print(f"Warning: Could not parse activity: {e}")
                continue
        
        return activities
    
    def _get_fallback_activities(self, city: str, day_number: int, budget: float) -> list[Activity]:
        """Fallback activities if AI generation fails"""
        daily_budget = budget * self.budget_utilization_target / 3
        return [
            Activity(
                name=f"Premium {city} Guided Tour",
                description=f"Expert-led tour of {city}'s top attractions with skip-the-line access",
                duration_hours=3.0,
                cost=daily_budget * 0.30,
                activity_type="sightseeing",
                time_slot="morning"
            ),
            Activity(
                name=f"Fine Dining at Top {city} Restaurant",
                description=f"Michelin-recommended restaurant experience with local specialties",
                duration_hours=2.0,
                cost=daily_budget * 0.25,
                activity_type="food",
                time_slot="afternoon"
            ),
            Activity(
                name=f"{city} Cultural Experience & Show",
                description=f"Traditional performance or cultural show unique to {city}",
                duration_hours=2.5,
                cost=daily_budget * 0.25,
                activity_type="cultural",
                time_slot="evening"
            ),
            Activity(
                name=f"Exclusive {city} Night Tour",
                description=f"Private evening tour showcasing {city}'s illuminated landmarks",
                duration_hours=2.0,
                cost=daily_budget * 0.20,
                activity_type="nightlife",
                time_slot="evening"
            )
        ]
    
    def validate_day_plan(self, day: DayPlan, daily_budget: float) -> tuple[bool, str]:
        """Validate a day plan against constraints."""
        if day.total_cost > daily_budget * 1.10:
            return False, f"Day {day.day_number} exceeds budget: ${day.total_cost:.2f} > ${daily_budget:.2f}"
        
        min_spend = daily_budget * self.min_daily_spend_ratio
        if day.total_cost < min_spend:
            return False, f"Day {day.day_number} underspends: ${day.total_cost:.2f} < ${min_spend:.2f}"
        
        if day.total_hours > self.hours_per_day:
            return False, f"Day {day.day_number} exceeds time limit: {day.total_hours:.1f}h > {self.hours_per_day}h"
        
        if len(day.activities) < 2:
            return False, f"Day {day.day_number} has too few activities: {len(day.activities)}"
        
        return True, ""
    
    def optimize_day_plan(self, day: DayPlan, daily_budget: float) -> DayPlan:
        """Optimize a day plan to fit within constraints"""
        time_slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
        day.activities.sort(key=lambda x: time_slot_order.get(x.time_slot, 1))
        
        while day.total_cost > daily_budget and len(day.activities) > 2:
            removable = [a for a in day.activities if a.cost > daily_budget * 0.3]
            if removable:
                to_remove = max(removable, key=lambda x: x.cost)
                day.activities.remove(to_remove)
                day.total_cost -= to_remove.cost
                day.total_hours -= to_remove.duration_hours
        
        while day.total_hours > self.hours_per_day and len(day.activities) > 2:
            longest = max(day.activities, key=lambda x: x.duration_hours)
            day.activities.remove(longest)
            day.total_cost -= longest.cost
            day.total_hours -= longest.duration_hours
        
        return day
    
    def replan_day(
        self, 
        city: str, 
        day_number: int, 
        failed_plan: DayPlan,
        remaining_budget: float,
        preferences: list[str],
        error_message: str
    ) -> DayPlan:
        """Re-plan a day that failed validation"""
        print(f"  🔄 Re-planning day {day_number}: {error_message}")
        
        prompt = f"""The previous plan for Day {day_number} in {city} failed validation.
Error: {error_message}
Previous plan cost: ${failed_plan.total_cost:.2f}
Previous plan hours: {failed_plan.total_hours:.1f}h

Create a NEW plan that:
1. Stays strictly under ${remaining_budget:.2f} budget
2. Uses maximum {self.hours_per_day} hours
3. Includes 3-4 activities
4. Matches preferences: {', '.join(preferences)}

Respond ONLY with valid JSON:
{{
    "activities": [
        {{
            "name": "Activity Name",
            "description": "Brief description",
            "duration_hours": 2.0,
            "cost": 30.0,
            "activity_type": "sightseeing",
            "time_slot": "morning"
        }}
    ]
}}"""
        
        response = self.llama.query(prompt, self.get_system_prompt())
        
        if not response:
            return self.optimize_day_plan(failed_plan, remaining_budget)
        
        data = self.llama.extract_json(response)
        
        if not data or 'activities' not in data:
            return self.optimize_day_plan(failed_plan, remaining_budget)
        
        new_day = DayPlan(day_number=day_number)
        
        for act_data in data['activities']:
            try:
                activity = Activity(
                    name=act_data.get('name', 'Unknown Activity'),
                    description=act_data.get('description', ''),
                    duration_hours=float(act_data.get('duration_hours', 2.0)),
                    cost=float(act_data.get('cost', 0.0)),
                    activity_type=act_data.get('activity_type', 'sightseeing'),
                    time_slot=act_data.get('time_slot', 'morning')
                )
                new_day.add_activity(activity)
            except (KeyError, ValueError):
                continue
        
        return new_day
    
    def create_travel_plan(self, user_input: UserInput) -> TravelPlan:
        """Main planning loop with constraint checking and re-planning."""
        print(f"\n{'='*60}")
        print(f"🌍 TRAVEL PLANNER AGENT")
        print(f"{'='*60}")
        print(f"📍 City: {user_input.city}")
        print(f"💰 Budget: ₹{user_input.budget:.0f}")
        print(f"📅 Days: {user_input.num_days}")
        print(f"🎯 Preferences: {', '.join(user_input.activity_preferences)}")
        print(f"{'='*60}\n")
        
        travel_plan = TravelPlan(
            city=user_input.city,
            budget=user_input.budget,
            num_days=user_input.num_days,
            preferences=user_input.activity_preferences
        )
        
        remaining_budget = user_input.budget
        daily_budget_target = user_input.budget / user_input.num_days
        all_previous_activities = []
        
        for day_num in range(1, user_input.num_days + 1):
            print(f"📅 Planning Day {day_num}...")
            print(f"   Budget remaining: ₹{remaining_budget:.0f}")
            print(f"   Target daily budget: ₹{daily_budget_target:.0f}")
            
            activities = self.generate_activities_for_day(
                city=user_input.city,
                day_number=day_num,
                remaining_budget=remaining_budget,
                preferences=user_input.activity_preferences,
                previous_activities=all_previous_activities
            )
            
            day_plan = DayPlan(day_number=day_num)
            for activity in activities:
                day_plan.add_activity(activity)
            
            is_valid, error_message = self.validate_day_plan(day_plan, daily_budget_target)
            
            replan_attempts = 0
            while not is_valid and replan_attempts < self.max_replanning_attempts:
                replan_attempts += 1
                day_plan = self.replan_day(
                    city=user_input.city,
                    day_number=day_num,
                    failed_plan=day_plan,
                    remaining_budget=min(remaining_budget, daily_budget_target * 1.2),
                    preferences=user_input.activity_preferences,
                    error_message=error_message
                )
                is_valid, error_message = self.validate_day_plan(day_plan, daily_budget_target)
            
            if not is_valid:
                print(f"   ⚠️ Applying final optimization for day {day_num}")
                day_plan = self.optimize_day_plan(day_plan, daily_budget_target)
            
            travel_plan.days.append(day_plan)
            remaining_budget -= day_plan.total_cost
            all_previous_activities.extend([a.name for a in day_plan.activities])
            
            print(f"   ✅ Day {day_num} planned: {len(day_plan.activities)} activities, ₹{day_plan.total_cost:.0f}")
        
        travel_plan.calculate_total_cost()
        
        if travel_plan.total_cost > user_input.budget:
            print(f"\n⚠️ Total cost ₹{travel_plan.total_cost:.0f} exceeds budget ₹{user_input.budget:.0f}")
            print("🔄 Applying global optimization...")
            travel_plan = self._global_budget_optimization(travel_plan, user_input.budget)
        
        return travel_plan
    
    def _global_budget_optimization(self, plan: TravelPlan, budget: float) -> TravelPlan:
        """Optimize the entire plan to fit within the global budget"""
        all_activities = []
        for day in plan.days:
            for activity in day.activities:
                all_activities.append((day, activity))
        
        all_activities.sort(key=lambda x: x[1].cost, reverse=True)
        
        for day, activity in all_activities:
            if plan.total_cost <= budget:
                break
            if len(day.activities) > 2:
                day.activities.remove(activity)
                day.total_cost -= activity.cost
                day.total_hours -= activity.duration_hours
                plan.total_cost -= activity.cost
        
        return plan
    
    def generate_itinerary_summary(self, plan: TravelPlan) -> str:
        """Generate a quick summary without extra API call for speed"""
        activity_types = set()
        activity_names = []
        for day in plan.days:
            for act in day.activities:
                activity_types.add(act.activity_type)
                activity_names.append(act.name)
        
        highlights = activity_names[:3] if len(activity_names) >= 3 else activity_names
        types_str = ", ".join(list(activity_types)[:3])
        
        savings = plan.budget - plan.total_cost
        if savings > 0:
            budget_msg = f"You'll save ₹{savings:.0f} from your budget!"
        else:
            budget_msg = "Your budget is fully optimized for this trip!"
        
        return f"Get ready for an amazing {plan.num_days}-day adventure in {plan.city}! Experience {types_str} with highlights like {', '.join(highlights)}. {budget_msg}"
