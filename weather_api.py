"""Weather API integration for fetching weather data."""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from models import WeatherHour
from config import get_config

logger = logging.getLogger(__name__)

class WeatherAPIClient:
    """Client for interacting with WeatherAPI.com"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://api.weatherapi.com/v1"
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, params: dict) -> dict:
        """Make a request to the WeatherAPI."""
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            raise
    
    def get_current_weather(self, location: str) -> Optional[WeatherHour]:
        """Get current weather data."""
        try:
            data = self._make_request('current.json', {'q': location, 'aqi': 'no'})
            
            current = data['current']
            current_time = datetime.fromtimestamp(current['last_updated_epoch'])
            
            return WeatherHour(
                datetime=current_time,
                temperature_f=current['temp_f'],
                uv_index=current.get('uv'),
                condition=current['condition']['text'],
                is_forecast=False
            )
        except Exception as e:
            logger.error(f"Error fetching current weather: {e}")
            return None
    
    def get_historical_weather(self, location: str, date: datetime) -> List[WeatherHour]:
        """Get historical weather data for a specific date."""
        try:
            date_str = date.strftime('%Y-%m-%d')
            data = self._make_request('history.json', {
                'q': location,
                'dt': date_str
            })
            
            weather_hours = []
            for hour_data in data['forecast']['forecastday'][0]['hour']:
                hour_time = datetime.fromtimestamp(hour_data['time_epoch'])
                
                weather_hours.append(WeatherHour(
                    datetime=hour_time,
                    temperature_f=hour_data['temp_f'],
                    uv_index=hour_data.get('uv'),
                    condition=hour_data['condition']['text'],
                    is_forecast=False
                ))
            
            return weather_hours
        except Exception as e:
            logger.error(f"Error fetching historical weather: {e}")
            return []
    
    def get_forecast_weather(self, location: str, days: int = 1) -> List[WeatherHour]:
        """Get forecast weather data."""
        try:
            data = self._make_request('forecast.json', {
                'q': location,
                'days': days,
                'aqi': 'no',
                'alerts': 'no'
            })
            
            weather_hours = []
            for day_data in data['forecast']['forecastday']:
                for hour_data in day_data['hour']:
                    hour_time = datetime.fromtimestamp(hour_data['time_epoch'])
                    
                    # Only include future hours
                    if hour_time > datetime.now():
                        weather_hours.append(WeatherHour(
                            datetime=hour_time,
                            temperature_f=hour_data['temp_f'],
                            uv_index=hour_data.get('uv'),
                            condition=hour_data['condition']['text'],
                            is_forecast=True
                        ))
            
            return weather_hours
        except Exception as e:
            logger.error(f"Error fetching forecast weather: {e}")
            return []
    
    def get_full_day_weather(self, location: str, target_date: Optional[datetime] = None) -> List[WeatherHour]:
        """Get complete weather data for a day (historical + current + forecast)."""
        if target_date is None:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_weather = []
        now = datetime.now()
        
        # Get historical data for the day (if target_date is today and some hours have passed)
        if target_date.date() == now.date() and now.hour > 0:
            historical = self.get_historical_weather(location, target_date)
            # Filter to only include hours that have already passed
            for hour in historical:
                if hour.datetime < now:
                    all_weather.append(hour)
        
        # Get current weather if target_date is today
        if target_date.date() == now.date():
            current = self.get_current_weather(location)
            if current:
                all_weather.append(current)
        
        # Get forecast data
        if target_date.date() >= now.date():
            forecast = self.get_forecast_weather(location, days=1)
            # Filter forecast to only include hours for the target date
            for hour in forecast:
                if hour.datetime.date() == target_date.date():
                    all_weather.append(hour)
        
        # Sort by datetime and remove duplicates
        all_weather.sort(key=lambda x: x.datetime)
        
        # Remove duplicates (keep the most recent data for each hour)
        unique_weather = {}
        for hour in all_weather:
            hour_key = hour.datetime.replace(minute=0, second=0, microsecond=0)
            if hour_key not in unique_weather or not hour.is_forecast:
                unique_weather[hour_key] = hour
        
        return list(unique_weather.values())
    
    def validate_location(self, location: str) -> bool:
        """Validate if a location is valid for the API.
        
        Supports multiple location formats:
        - City names: "New York"
        - City, State: "Phoenix, AZ"
        - City, Country: "London, UK"
        - Zip codes: "10001" or "90210"
        - Coordinates: "40.7128,-74.0060"
        """
        try:
            self._make_request('current.json', {'q': location, 'aqi': 'no'})
            return True
        except:
            return False

def create_weather_client() -> WeatherAPIClient:
    """Create a weather client using the configured API key."""
    config = get_config()
    return WeatherAPIClient(config.weather_api_key) 