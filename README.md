# Player Readiness Web Application

A modern web application for tracking player performance metrics and readiness indicators for Boston Bolts MLS Next teams.

## Features

- **User Authentication**: Secure login and signup system
- **Player Dashboard**: Personalized performance overview
- **Readiness Gauges**: Visual indicators for key performance metrics
- **Technical Charts**: Performance trends and analytics (coming soon)
- **Physical Rankings**: Player rankings and comparisons (coming soon)
- **Modern UI**: Responsive design with Bootstrap 5 and custom styling

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### 3. First Time Setup

1. Visit the application in your browser
2. Click "Sign Up" to create a new account
3. Fill in your player information and select your team
4. Log in with your credentials
5. View your personalized dashboard

## Data Structure

The application expects player data files in the `Player Data/` directory with the following naming convention:
- `U15 MLS Next_PD_Data.csv`
- `U16 MLS Next_PD_Data.csv`
- `U17 MLS Next_PD_Data.csv`
- etc.

## Supported Teams

- U15 MLS Next
- U16 MLS Next
- U17 MLS Next
- U19 MLS Next
- U15 MLS Next 2
- U16 MLS Next 2
- U17 MLS Next 2
- U19 MLS Next 2

## Performance Metrics

The application tracks the following key metrics:
- **Distance (m)**: Total distance covered
- **High Intensity Running (m)**: High-speed running distance
- **Sprint Distance (m)**: Distance covered during sprints
- **No. of Sprints**: Number of sprint events
- **Top Speed (kph)**: Maximum speed achieved

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Charts**: Plotly.js
- **Icons**: Font Awesome

## Development

To run in development mode with auto-reload:

```bash
export FLASK_ENV=development
python app.py
```

## Security Notes

- Change the `SECRET_KEY` in `app.py` for production use
- Consider using environment variables for sensitive configuration
- Implement proper password policies for production deployment

## License

This application is developed for Boston Bolts MLS Next teams. 