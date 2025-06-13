#!/usr/bin/env python3
"""
Test script for enhanced surface recovery logic with real data
"""

import os
import logging
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from models import WeatherHour, RiskScore
from config import RiskConfig, AppConfig, get_config
from risk_calculator import RiskCalculator
from constants import SURFACE_COOLING_COEFFICIENTS
from models import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_db_data():
    """Load real weather data from the database."""
    config = get_config()
    db_manager = DatabaseManager(config.database_path)
    
    # Get data from the past 24 hours
    end_date = datetime.now() 
    start_date = end_date - timedelta(hours=24)
    
    try:
        return db_manager.get_weather_data(start_date, end_date)
    except Exception as e:
        logger.error(f"Error loading data from database: {e}")
        return []

def compare_recovery_settings(weather_data):
    """Compare different recovery settings with real weather data."""
    if not weather_data:
        logger.error("No weather data available for testing")
        return
    
    print(f"Loaded {len(weather_data)} hours of weather data from database")
    print(f"Temperature range: {min(h.temperature_f for h in weather_data):.1f}°F - {max(h.temperature_f for h in weather_data):.1f}°F")
    
    # Test configs
    configs = [
        # Default settings
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=False,
            enable_time_of_day_factor=False
        ),
        # All enhanced features
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=True,
            enable_time_of_day_factor=True,
            surface_max_recovery_score=2.0,
            surface_type="asphalt"
        ),
    ]
    
    # Test each configuration
    all_results = []
    
    for i, config in enumerate(configs):
        calculator = RiskCalculator(config)
        risk_scores = calculator.calculate_risk_scores(weather_data)
        all_results.append(risk_scores)
        
        label = "Default" if i == 0 else "Enhanced"
        print(f"\n=== {label} Recovery Settings ===")
        
        high_risk = [s for s in risk_scores if s.recommend_shoes]
        print(f"High Risk Hours: {len(high_risk)} out of {len(risk_scores)}")
        
        if high_risk:
            times = [s.datetime.strftime("%H:%M") for s in high_risk]
            print(f"High Risk Times: {', '.join(times)}")
            
        # Show recovery score impact
        recovery_impact = sum(abs(s.surface_recovery_score) for s in risk_scores)
        print(f"Total Recovery Impact: {recovery_impact:.2f}")
        print(f"Average Recovery Score: {recovery_impact/len(risk_scores):.2f}")
    
    # Visualize the results
    visualize_comparison(weather_data, all_results)

def visualize_comparison(weather_data, result_sets):
    """Create visualization comparing different recovery strategies with real data."""
    plt.figure(figsize=(14, 10))
    
    # Extract time and temperatures for plotting
    times = [hour.datetime for hour in weather_data]
    temps = [hour.temperature_f for hour in weather_data]
    
    # Plot temperature
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(times, temps, 'r-', linewidth=2)
    ax1.set_ylabel('Temperature (°F)')
    ax1.set_title('Temperature Profile')
    ax1.axhline(y=90, color='r', linestyle='--', alpha=0.7)
    ax1.text(times[0], 91, "Recovery Threshold (90°F)", color='r')
    ax1.grid(True, alpha=0.3)
    
    # Plot recovery scores
    ax2 = plt.subplot(3, 1, 2, sharex=ax1)
    
    # Add labels for legend
    labels = ['Default Recovery', 'Enhanced Recovery']
    linestyles = ['-', '--']
    colors = ['blue', 'green']
    
    for i, results in enumerate(result_sets):
        recovery_scores = [score.surface_recovery_score for score in results]
        ax2.plot(times, recovery_scores, linestyle=linestyles[i], color=colors[i], linewidth=2, label=labels[i])
    
    ax2.set_ylabel('Recovery Score')
    ax2.set_title('Surface Recovery Scores Comparison')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot total risk scores
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    
    for i, results in enumerate(result_sets):
        total_scores = [score.total_score for score in results]
        ax3.plot(times, total_scores, linestyle=linestyles[i], color=colors[i], linewidth=2, label=labels[i])
    
    # Add threshold line
    ax3.axhline(y=6.0, color='red', linestyle='--', alpha=0.7, label='Shoe Threshold (6.0)')
    
    ax3.set_ylabel('Total Risk Score')
    ax3.set_title('Total Risk Score Comparison (Real Weather Data)')
    ax3.set_xlabel('Time')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Format x-axis
    for ax in [ax1, ax2, ax3]:
        ax.set_xlim(times[0], times[-1])
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('real_data_comparison.png')
    plt.show()

if __name__ == "__main__":
    print("Testing enhanced surface recovery logic with real data")
    weather_data = load_db_data()
    if weather_data:
        compare_recovery_settings(weather_data)
    else:
        print("No data available. Please ensure you've run the app to collect weather data first.") 