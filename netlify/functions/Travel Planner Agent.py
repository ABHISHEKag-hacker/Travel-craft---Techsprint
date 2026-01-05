"""
Travel Planner Agent with Budget Constraints
=============================================
An agentic AI system that creates travel itineraries using LLM models.
Features:
- Breaks plans into days
- Allocates activities within time + budget constraints
- Re-plans if budget is exceeded
- Generates final itinerary + cost breakdown

Requirements:
- pip install openai
- OpenRouter API key
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

# OpenRouter API Configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


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
    
    def __init__(self, model_name: str = "nex-agi/deepseek-v3.1-nex-n1:free"):
        self.model_name = model_name
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
                max_tokens=800
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
    
    def __init__(self, model_name: str = "nex-agi/deepseek-v3.1-nex-n1:free"):
        self.llama = LlamaAgent(model_name)
        self.max_replanning_attempts = 1  # Reduced for speed
        self.hours_per_day = 10  # Available hours for activities per day
        self.budget_utilization_target = 0.85  # Target 85% of budget
        self.min_daily_spend_ratio = 0.50  # Reduced for flexibility
        
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
        
        # Calculate target daily spend (aim for 85% budget utilization)
        target_daily_spend = remaining_budget * self.budget_utilization_target / max(1, (self.hours_per_day // 3))  # Rough days remaining estimate
        if day_number == 1:
            target_daily_spend = remaining_budget * self.budget_utilization_target / 3  # Assume 3-4 day trip on day 1
        
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
        """Fallback activities if AI generation fails - Now with premium pricing"""
        daily_budget = budget * self.budget_utilization_target / 3  # Target 85% utilization over 3 days
        return [
            Activity(
                name=f"Premium {city} Guided Tour",
                description=f"Expert-led tour of {city}'s top attractions with skip-the-line access",
                duration_hours=3.0,
                cost=daily_budget * 0.30,  # 30% of daily budget
                activity_type="sightseeing",
                time_slot="morning"
            ),
            Activity(
                name=f"Fine Dining at Top {city} Restaurant",
                description=f"Michelin-recommended restaurant experience with local specialties",
                duration_hours=2.0,
                cost=daily_budget * 0.25,  # 25% of daily budget
                activity_type="food",
                time_slot="afternoon"
            ),
            Activity(
                name=f"{city} Cultural Experience & Show",
                description=f"Traditional performance or cultural show unique to {city}",
                duration_hours=2.5,
                cost=daily_budget * 0.25,  # 25% of daily budget
                activity_type="cultural",
                time_slot="evening"
            ),
            Activity(
                name=f"Exclusive {city} Night Tour",
                description=f"Private evening tour showcasing {city}'s illuminated landmarks",
                duration_hours=2.0,
                cost=daily_budget * 0.20,  # 20% of daily budget
                activity_type="nightlife",
                time_slot="evening"
            )
        ]
    
    def validate_day_plan(self, day: DayPlan, daily_budget: float) -> tuple[bool, str]:
        """
        Validate a day plan against constraints.
        Returns (is_valid, error_message)
        """
        # Check budget constraint - allow up to 110% of daily budget
        if day.total_cost > daily_budget * 1.10:
            return False, f"Day {day.day_number} exceeds budget: ${day.total_cost:.2f} > ${daily_budget:.2f}"
        
        # Check MINIMUM spending - must spend at least 70% of daily budget
        min_spend = daily_budget * self.min_daily_spend_ratio
        if day.total_cost < min_spend:
            return False, f"Day {day.day_number} underspends: ${day.total_cost:.2f} < ${min_spend:.2f} (minimum 70%)"
        
        # Check time constraint
        if day.total_hours > self.hours_per_day:
            return False, f"Day {day.day_number} exceeds time limit: {day.total_hours:.1f}h > {self.hours_per_day}h"
        
        # Check minimum activities
        if len(day.activities) < 2:
            return False, f"Day {day.day_number} has too few activities: {len(day.activities)}"
        
        return True, ""
    
    def optimize_day_plan(
        self, 
        day: DayPlan, 
        daily_budget: float
    ) -> DayPlan:
        """Optimize a day plan to fit within constraints"""
        
        # Sort activities by preference score (keeping time slots in order)
        time_slot_order = {"morning": 0, "afternoon": 1, "evening": 2}
        day.activities.sort(key=lambda x: time_slot_order.get(x.time_slot, 1))
        
        # Remove activities until we're within budget
        while day.total_cost > daily_budget and len(day.activities) > 2:
            # Find the most expensive activity that's not essential
            removable = [a for a in day.activities if a.cost > daily_budget * 0.3]
            if removable:
                to_remove = max(removable, key=lambda x: x.cost)
                day.activities.remove(to_remove)
                day.total_cost -= to_remove.cost
                day.total_hours -= to_remove.duration_hours
        
        # Remove activities until we're within time limits
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
            # Return optimized version of failed plan
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
        """
        Main planning loop with constraint checking and re-planning.
        
        This is the agentic loop that:
        1. Plans each day
        2. Validates against constraints
        3. Re-plans if necessary
        4. Optimizes the final itinerary
        """
        
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
        
        # ====== AGENTIC PLANNING LOOP ======
        for day_num in range(1, user_input.num_days + 1):
            print(f"📅 Planning Day {day_num}...")
            print(f"   Budget remaining: ₹{remaining_budget:.0f}")
            print(f"   Target daily budget: ₹{daily_budget_target:.0f}")
            
            # Step 1: PLAN - Generate initial activities
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
            
            # Step 2: CHECK - Validate against constraints
            is_valid, error_message = self.validate_day_plan(day_plan, daily_budget_target)
            
            # Step 3: RE-PLAN if needed
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
            
            # Final optimization if still invalid
            if not is_valid:
                print(f"   ⚠️ Applying final optimization for day {day_num}")
                day_plan = self.optimize_day_plan(day_plan, daily_budget_target)
            
            # Update tracking
            travel_plan.days.append(day_plan)
            remaining_budget -= day_plan.total_cost
            all_previous_activities.extend([a.name for a in day_plan.activities])
            
            print(f"   ✅ Day {day_num} planned: {len(day_plan.activities)} activities, ₹{day_plan.total_cost:.0f}")
        
        # Calculate final totals
        travel_plan.calculate_total_cost()
        
        # Final budget check and adjustment
        if travel_plan.total_cost > user_input.budget:
            print(f"\n⚠️ Total cost ₹{travel_plan.total_cost:.0f} exceeds budget ₹{user_input.budget:.0f}")
            print("🔄 Applying global optimization...")
            travel_plan = self._global_budget_optimization(travel_plan, user_input.budget)
        
        return travel_plan
    
    def _global_budget_optimization(self, plan: TravelPlan, budget: float) -> TravelPlan:
        """Optimize the entire plan to fit within the global budget"""
        
        over_budget = plan.total_cost - budget
        
        # Find activities that can be removed or reduced
        all_activities = []
        for day in plan.days:
            for activity in day.activities:
                all_activities.append((day, activity))
        
        # Sort by cost (highest first)
        all_activities.sort(key=lambda x: x[1].cost, reverse=True)
        
        # Remove expensive activities until within budget
        for day, activity in all_activities:
            if plan.total_cost <= budget:
                break
            if len(day.activities) > 2:  # Keep at least 2 activities per day
                day.activities.remove(activity)
                day.total_cost -= activity.cost
                day.total_hours -= activity.duration_hours
                plan.total_cost -= activity.cost
        
        return plan
    
    def generate_itinerary_summary(self, plan: TravelPlan) -> str:
        """Generate a quick summary without extra API call for speed"""
        
        # Get unique activity types
        activity_types = set()
        activity_names = []
        for day in plan.days:
            for act in day.activities:
                activity_types.add(act.activity_type)
                activity_names.append(act.name)
        
        # Generate quick local summary
        highlights = activity_names[:3] if len(activity_names) >= 3 else activity_names
        types_str = ", ".join(list(activity_types)[:3])
        
        savings = plan.budget - plan.total_cost
        if savings > 0:
            budget_msg = f"You'll save ₹{savings:.0f} from your budget!"
        else:
            budget_msg = "Your budget is fully optimized for this trip!"
        
        return f"Get ready for an amazing {plan.num_days}-day adventure in {plan.city}! Experience {types_str} with highlights like {', '.join(highlights)}. {budget_msg}"
    
    def print_itinerary(self, plan: TravelPlan):
        """Print a beautifully formatted itinerary"""
        
        print(f"\n{'='*70}")
        print(f"{'🌴 FINAL TRAVEL ITINERARY 🌴':^70}")
        print(f"{'='*70}")
        print(f"\n📍 Destination: {plan.city}")
        print(f"💰 Budget: ₹{plan.budget:.0f}")
        print(f"📅 Duration: {plan.num_days} days")
        print(f"🎯 Preferences: {', '.join(plan.preferences)}")
        print(f"\n{'-'*70}")
        
        for day in plan.days:
            print(f"\n{'📅 DAY ' + str(day.day_number):=^70}")
            print(f"{'Daily Budget: ₹' + f'{day.total_cost:.0f}':^70}")
            print(f"{'-'*70}")
            
            # Sort activities by time slot
            time_order = {"morning": 0, "afternoon": 1, "evening": 2}
            sorted_activities = sorted(day.activities, key=lambda x: time_order.get(x.time_slot, 1))
            
            for activity in sorted_activities:
                emoji = self._get_activity_emoji(activity.activity_type)
                print(f"\n  {emoji} {activity.name}")
                print(f"     ⏰ Time: {activity.time_slot.capitalize()} ({activity.duration_hours}h)")
                print(f"     💵 Cost: ₹{activity.cost:.0f}")
                print(f"     📝 {activity.description}")
        
        # Cost Breakdown
        print(f"\n{'='*70}")
        print(f"{'💰 COST BREAKDOWN 💰':^70}")
        print(f"{'='*70}")
        
        for day in plan.days:
            print(f"  Day {day.day_number}: ₹{day.total_cost:.0f}")
        
        print(f"  {'-'*40}")
        print(f"  {'TOTAL':.<35} ₹{plan.total_cost:.0f}")
        print(f"  {'BUDGET':.<35} ₹{plan.budget:.0f}")
        print(f"  {'REMAINING':.<35} ₹{plan.budget - plan.total_cost:.0f}")
        
        if plan.total_cost <= plan.budget:
            print(f"\n  ✅ Within budget! You have ₹{plan.budget - plan.total_cost:.0f} to spare!")
        else:
            print(f"\n  ⚠️ Over budget by ₹{plan.total_cost - plan.budget:.0f}")
        
        # Generate AI summary
        print(f"\n{'='*70}")
        print(f"{'✨ TRIP SUMMARY ✨':^70}")
        print(f"{'='*70}")
        summary = self.generate_itinerary_summary(plan)
        print(f"\n{summary}")
        print(f"\n{'='*70}")
    
    def _get_activity_emoji(self, activity_type: str) -> str:
        """Get an emoji for the activity type"""
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


# ============================================================================
# Interactive CLI Interface
# ============================================================================

def get_user_input() -> UserInput:
    """Interactive CLI to get user input"""
    
    print("\n" + "="*60)
    print("🌍 WELCOME TO AI TRAVEL PLANNER 🌍".center(60))
    print("="*60)
    print("\nPowered by Llama AI - Let's plan your perfect trip!\n")
    
    # Get budget
    while True:
        try:
            budget = float(input("💰 Enter your total budget (in ₹ INR): ₹"))
            if budget > 0:
                break
            print("Please enter a positive amount.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get number of days
    while True:
        try:
            num_days = int(input("📅 Enter number of days: "))
            if 1 <= num_days <= 30:
                break
            print("Please enter between 1 and 30 days.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Get city
    city = input("📍 Enter your destination city: ").strip()
    while not city:
        city = input("Please enter a valid city name: ").strip()
    
    # Get preferences
    print("\n🎯 Activity Preferences (choose from the list):")
    print("   1. Sightseeing    2. Adventure    3. Cultural")
    print("   4. Food           5. Relaxation   6. Shopping")
    print("   7. Nightlife")
    
    pref_input = input("\nEnter preference numbers separated by commas (e.g., 1,3,4): ").strip()
    
    pref_map = {
        "1": "sightseeing",
        "2": "adventure", 
        "3": "cultural",
        "4": "food",
        "5": "relaxation",
        "6": "shopping",
        "7": "nightlife"
    }
    
    preferences = []
    for p in pref_input.split(","):
        p = p.strip()
        if p in pref_map:
            preferences.append(pref_map[p])
    
    if not preferences:
        preferences = ["sightseeing", "food", "cultural"]  # Default preferences
    
    return UserInput(
        budget=budget,
        num_days=num_days,
        city=city,
        activity_preferences=preferences
    )


def main():
    """Main entry point"""
    
    print("\n" + "="*60)
    print("🌍 AI TRAVEL PLANNER AGENT 🌍".center(60))
    print("="*60)
    print("\nChoose an option:")
    print("  1. Interactive Mode (Enter your own travel details)")
    print("  2. Exit")
    
    choice = input("\nEnter your choice (1/2): ").strip()
    
    if choice == "1":
        user_input = get_user_input()
        agent = TravelPlannerAgent()  # Uses OpenRouter with Llama 3.3
        travel_plan = agent.create_travel_plan(user_input)
        agent.print_itinerary(travel_plan)
        
    elif choice == "2":
        print("\n👋 Goodbye! Happy travels!")
        return
    else:
        print("Invalid choice. Please run the program again.")


if __name__ == "__main__":
    main()
