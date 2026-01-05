# 🌍 AI Travel Planner

An intelligent travel planning application powered by AI that creates personalized travel itineraries with budget optimization.

## ✨ Features

- **AI-Powered Itineraries** - Uses DeepSeek AI via OpenRouter to generate custom travel plans
- **Budget Management** - Smart budget allocation across activities, travel, and hotel
- **Hotel Booking** - Select star rating (2-5) and AC/Non-AC rooms
- **Travel Cost Estimation** - Calculates travel costs between Indian cities
- **Multi-Traveler Support** - Plan for adults and children with appropriate pricing
- **PDF Download** - Export your itinerary as a beautiful PDF document
- **Responsive Design** - Works on desktop and mobile devices

## 📁 Project Structure

```
hackathon/
├── agents/                    # AI Agent modules
│   ├── __init__.py
│   └── travel_planner.py     # Main travel planning AI agent
│
├── api/                       # Backend API
│   ├── __init__.py
│   ├── app.py                # Flask application factory
│   ├── routes/
│   │   ├── __init__.py
│   │   └── travel.py         # Travel planning endpoints
│   └── utils/
│       ├── __init__.py
│       ├── cost_calculator.py # Travel & hotel cost functions
│       └── pdf_generator.py   # PDF generation utility
│
├── config/                    # Configuration
│   ├── __init__.py
│   └── settings.py           # API keys, app settings
│
├── frontend/                  # Frontend assets
│   ├── templates/
│   │   └── index.html        # Main HTML template
│   └── static/
│       ├── css/              # Stylesheets
│       └── js/               # JavaScript files
│
├── netlify/                   # Netlify deployment
│   └── functions/
│       └── handler.py        # Serverless function handler
│
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── run.py                    # Development server entry point
├── netlify.toml              # Netlify configuration
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hackathon
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   ```bash
   copy .env.example .env
   # Edit .env with your API key
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Open in browser**
   ```
   http://localhost:5000
   ```

## 🔧 Configuration

Edit `config/settings.py` or use environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | OpenRouter API key | (included) |
| `DEBUG` | Enable debug mode | `True` |
| `PORT` | Server port | `5000` |
| `DEFAULT_MODEL` | AI model to use | `nex-agi/deepseek-v3.1-nex-n1:free` |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/plan` | POST | Generate travel plan |
| `/download-pdf` | POST | Download PDF itinerary |

### POST /plan Request Body
```json
{
  "budget": 50000,
  "days": 3,
  "city": "Goa",
  "adults": 2,
  "children": 1,
  "preferences": ["sightseeing", "food", "adventure"],
  "origin_city": "Mumbai",
  "include_hotel": true,
  "hotel_rating": 4,
  "room_type": "ac"
}
```

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Flask API │────▶│  AI Agent   │
│  (HTML/JS)  │◀────│  (Routes)   │◀────│ (DeepSeek)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Utils     │
                    │ - Cost Calc │
                    │ - PDF Gen   │
                    └─────────────┘
```

## 🌐 Deployment

### Netlify
The project is configured for Netlify deployment:

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
netlify deploy --prod
```

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
