"""
Cost Calculator Utilities
==========================
Functions to estimate travel and hotel costs.
"""


def estimate_travel_cost(origin: str, destination: str) -> float:
    """
    Estimate travel cost based on origin and destination cities in India.
    Uses approximate pricing for train/bus travel.
    """
    # Common Indian city pairs with approximate distances (in km)
    city_distances = {
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
    
    # Price per km (mix of train and bus rates)
    price_per_km = 2.5
    
    # Round trip
    travel_cost = distance * price_per_km * 2
    
    # Add buffer for local transport
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
    
    # City-based multiplier
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


def get_activity_emoji(activity_type: str) -> str:
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
