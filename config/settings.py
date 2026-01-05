# Configuration settings for the Travel Planner application
import os
from pathlib import Path

# Find project root and load .env from there
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / '.env'

# Load dotenv if available
try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        print(f"✅ Loaded environment from {ENV_FILE}")
    else:
        print(f"⚠️ No .env file found at {ENV_FILE}")
except ImportError:
    print("⚠️ python-dotenv not installed. Using system environment variables only.")

# API Configuration
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Validate API Key
if not OPENROUTER_API_KEY:
    print("="*60)
    print("❌ ERROR: OPENROUTER_API_KEY not set!")
    print("="*60)
    print("Please create a .env file in the project root with:")
    print("   OPENROUTER_API_KEY=your-api-key-here")
    print("")
    print("Or set it as an environment variable.")
    print("="*60)

# Model Configuration
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'xiaomi/mimo-v2-flash:free')

# Application Settings
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))
SECRET_KEY = os.environ.get('SECRET_KEY', 'travel-planner-secret-key-2024')

# Agent Settings
MAX_REPLANNING_ATTEMPTS = 1
HOURS_PER_DAY = 10
BUDGET_UTILIZATION_TARGET = 0.85
MIN_DAILY_SPEND_RATIO = 0.50
MAX_TOKENS = 800
