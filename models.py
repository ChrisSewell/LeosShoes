"""Data models for weather and risk assessment."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class WeatherHour:
    """Represents weather data for a single hour."""
    datetime: datetime
    temperature_f: float
    uv_index: Optional[float]
    condition: str
    is_forecast: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'datetime': self.datetime.isoformat(),
            'temperature_f': self.temperature_f,
            'uv_index': self.uv_index,
            'condition': self.condition,
            'is_forecast': self.is_forecast
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WeatherHour':
        """Create from dictionary."""
        return cls(
            datetime=datetime.fromisoformat(data['datetime']),
            temperature_f=data['temperature_f'],
            uv_index=data.get('uv_index'),
            condition=data['condition'],
            is_forecast=data.get('is_forecast', False)
        )

@dataclass
class RiskScore:
    """Represents a risk score for a specific hour."""
    datetime: datetime
    temperature_score: float
    uv_score: float
    condition_score: float
    accumulated_heat_score: float
    surface_recovery_score: float
    total_score: float
    recommend_shoes: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'datetime': self.datetime.isoformat(),
            'temperature_score': self.temperature_score,
            'uv_score': self.uv_score,
            'condition_score': self.condition_score,
            'accumulated_heat_score': self.accumulated_heat_score,
            'surface_recovery_score': self.surface_recovery_score,
            'total_score': self.total_score,
            'recommend_shoes': self.recommend_shoes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RiskScore':
        """Create from dictionary."""
        return cls(
            datetime=datetime.fromisoformat(data['datetime']),
            temperature_score=data['temperature_score'],
            uv_score=data['uv_score'],
            condition_score=data['condition_score'],
            accumulated_heat_score=data['accumulated_heat_score'],
            surface_recovery_score=data['surface_recovery_score'],
            total_score=data['total_score'],
            recommend_shoes=data['recommend_shoes']
        )

class DatabaseManager:
    """Manages database operations for weather and risk data."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Weather data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT UNIQUE,
                    temperature_f REAL,
                    uv_index REAL,
                    condition TEXT,
                    is_forecast BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Risk scores table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT UNIQUE,
                    temperature_score REAL,
                    uv_score REAL,
                    condition_score REAL,
                    accumulated_heat_score REAL,
                    surface_recovery_score REAL,
                    total_score REAL,
                    recommend_shoes BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_datetime ON weather_data(datetime)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_datetime ON risk_scores(datetime)')
            
            conn.commit()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()
    
    def save_weather_data(self, weather_hours: List[WeatherHour]):
        """Save weather data to database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            for hour in weather_hours:
                cursor.execute('''
                    INSERT OR REPLACE INTO weather_data 
                    (datetime, temperature_f, uv_index, condition, is_forecast)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    hour.datetime.isoformat(),
                    hour.temperature_f,
                    hour.uv_index,
                    hour.condition,
                    hour.is_forecast
                ))
            
            conn.commit()
            logger.info(f"Saved {len(weather_hours)} weather records")
            
        except Exception as e:
            logger.error(f"Error saving weather data: {e}")
            raise
        finally:
            conn.close()
    
    def save_risk_scores(self, risk_scores: List[RiskScore]):
        """Save risk scores to database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            for score in risk_scores:
                cursor.execute('''
                    INSERT OR REPLACE INTO risk_scores 
                    (datetime, temperature_score, uv_score, condition_score, 
                     accumulated_heat_score, surface_recovery_score, total_score, recommend_shoes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    score.datetime.isoformat(),
                    score.temperature_score,
                    score.uv_score,
                    score.condition_score,
                    score.accumulated_heat_score,
                    score.surface_recovery_score,
                    score.total_score,
                    score.recommend_shoes
                ))
            
            conn.commit()
            logger.info(f"Saved {len(risk_scores)} risk score records")
            
        except Exception as e:
            logger.error(f"Error saving risk scores: {e}")
            raise
        finally:
            conn.close()
    
    def get_weather_data(self, start_date: datetime, end_date: datetime) -> List[WeatherHour]:
        """Retrieve weather data for a date range."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT datetime, temperature_f, uv_index, condition, is_forecast
                FROM weather_data
                WHERE datetime BETWEEN ? AND ?
                ORDER BY datetime
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                results.append(WeatherHour(
                    datetime=datetime.fromisoformat(row[0]),
                    temperature_f=row[1],
                    uv_index=row[2],
                    condition=row[3],
                    is_forecast=bool(row[4])
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving weather data: {e}")
            raise
        finally:
            conn.close()
    
    def get_risk_scores(self, start_date: datetime, end_date: datetime) -> List[RiskScore]:
        """Retrieve risk scores for a date range."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT datetime, temperature_score, uv_score, condition_score,
                       accumulated_heat_score, surface_recovery_score, total_score, recommend_shoes
                FROM risk_scores
                WHERE datetime BETWEEN ? AND ?
                ORDER BY datetime
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                results.append(RiskScore(
                    datetime=datetime.fromisoformat(row[0]),
                    temperature_score=row[1],
                    uv_score=row[2],
                    condition_score=row[3],
                    accumulated_heat_score=row[4],
                    surface_recovery_score=row[5],
                    total_score=row[6],
                    recommend_shoes=bool(row[7])
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving risk scores: {e}")
            raise
        finally:
            conn.close() 