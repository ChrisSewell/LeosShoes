"""Configuration management for paw burn risk assessment."""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables
load_dotenv()

@dataclass
class RiskConfig:
    """Configuration for risk assessment parameters."""
    temp_threshold_low: float = 80.0
    temp_threshold_med: float = 90.0
    temp_threshold_high: float = 100.0
    
    uv_threshold_low: float = 6.0
    uv_threshold_med: float = 8.0
    uv_threshold_high: float = 10.0
    
    risk_threshold_shoes: float = 6.0
    rolling_window_hours: int = 2
    surface_recovery_hours: int = 2
    
    # Surface recovery enhancement parameters
    surface_recovery_temp_threshold: float = 90.0
    surface_type: str = "asphalt"  # Options: asphalt, concrete, mixed, grass
    surface_max_recovery_score: float = 2.0
    enable_graduated_recovery: bool = True
    enable_time_of_day_factor: bool = True
    
    # Display preferences
    use_24hr_time: bool = False  # False for 12hr time format, True for 24hr
    
    @classmethod
    def from_env(cls) -> 'RiskConfig':
        """Create configuration from environment variables."""
        return cls(
            temp_threshold_low=float(os.getenv('TEMP_THRESHOLD_LOW', 80)),
            temp_threshold_med=float(os.getenv('TEMP_THRESHOLD_MED', 90)),
            temp_threshold_high=float(os.getenv('TEMP_THRESHOLD_HIGH', 100)),
            uv_threshold_low=float(os.getenv('UV_THRESHOLD_LOW', 6)),
            uv_threshold_med=float(os.getenv('UV_THRESHOLD_MED', 8)),
            uv_threshold_high=float(os.getenv('UV_THRESHOLD_HIGH', 10)),
            risk_threshold_shoes=float(os.getenv('RISK_THRESHOLD_SHOES', 6)),
            rolling_window_hours=int(os.getenv('ROLLING_WINDOW_HOURS', 2)),
            surface_recovery_hours=int(os.getenv('SURFACE_RECOVERY_HOURS', 2)),
            # Surface recovery enhancement parameters
            surface_recovery_temp_threshold=float(os.getenv('SURFACE_RECOVERY_TEMP_THRESHOLD', 90)),
            surface_type=os.getenv('SURFACE_TYPE', 'asphalt'),
            surface_max_recovery_score=float(os.getenv('SURFACE_MAX_RECOVERY_SCORE', 2.0)),
            enable_graduated_recovery=os.getenv('ENABLE_GRADUATED_RECOVERY', 'true').lower() == 'true',
            enable_time_of_day_factor=os.getenv('ENABLE_TIME_OF_DAY_FACTOR', 'true').lower() == 'true',
            # Display preferences
            use_24hr_time=os.getenv('USE_24HR_TIME', 'false').lower() == 'true'
        )

@dataclass
class AppConfig:
    """Main application configuration."""
    weather_api_key: str
    default_location: str = "New York"
    database_path: str = "paw_risk.db"
    risk_config: RiskConfig = None
    
    def __post_init__(self):
        if self.risk_config is None:
            self.risk_config = RiskConfig.from_env()
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create configuration from environment variables."""
        api_key = os.getenv('WEATHER_API_KEY')
        if not api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")
        
        return cls(
            weather_api_key=api_key,
            default_location=os.getenv('DEFAULT_LOCATION', 'New York'),
            database_path=os.getenv('DATABASE_PATH', 'paw_risk.db'),
            risk_config=RiskConfig.from_env()
        )

# Global configuration instance
config = None

def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global config
    if config is None:
        config = AppConfig.from_env()
    return config 