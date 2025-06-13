#!/usr/bin/env python3
"""
Test script for enhanced surface recovery logic
"""

import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from models import WeatherHour
from config import RiskConfig
from risk_calculator import RiskCalculator
from constants import SURFACE_COOLING_COEFFICIENTS

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_data():
    """Create synthetic test data with a temperature peak followed by cooling."""
    now = datetime.now()
    hours = []
    
    # Create a 24-hour dataset
    for i in range(24):
        # Time starting from 24 hours ago to now
        time = now - timedelta(hours=24-i)
        
        # Temperature pattern: starts low, peaks in afternoon, drops at night
        if i < 8:  # Early morning (cold)
            temp = 75.0 + i * 1.5
            condition = "Clear"
            uv = 0.0
        elif i < 14:  # Mid-day heating (peak at 2pm / hour 14)
            temp = 85.0 + (i - 8) * 3.0
            condition = "Sunny"
            uv = 8.0
        else:  # Afternoon cooling
            temp = 95.0 - (i - 14) * 2.0
            condition = "Partly Cloudy" if i < 18 else "Clear"
            uv = max(0.0, 8.0 - (i - 14) * 1.5)
        
        # Create a peak temperature that exceeds threshold
        if i == 13:  # 1pm
            temp = 95.0  # Peak temperature
        
        hours.append(WeatherHour(
            datetime=time,
            temperature_f=temp,
            uv_index=uv,
            condition=condition,
            is_forecast=False
        ))
    
    return hours

def visualize_results(test_data, all_results):
    """Create visualization comparing different recovery strategies."""
    plt.figure(figsize=(14, 10))
    
    # Extract time and temperatures for plotting
    times = [hour.datetime for hour in test_data]
    temps = [hour.temperature_f for hour in test_data]
    
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
    labels = ['Default', 'Graduated', 'Time-of-day', 'All Features', 'Concrete', 'Grass']
    linestyles = ['-', '--', ':', '-.', '--', ':']
    colors = ['blue', 'green', 'purple', 'orange', 'brown', 'magenta']
    
    for i, results in enumerate(all_results):
        recovery_scores = [score.surface_recovery_score for score in results]
        ax2.plot(times, recovery_scores, linestyle=linestyles[i], color=colors[i], linewidth=2, label=labels[i])
    
    ax2.set_ylabel('Recovery Score')
    ax2.set_title('Surface Recovery Scores Comparison')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Plot total risk scores
    ax3 = plt.subplot(3, 1, 3, sharex=ax1)
    
    for i, results in enumerate(all_results):
        total_scores = [score.total_score for score in results]
        ax3.plot(times, total_scores, linestyle=linestyles[i], color=colors[i], linewidth=2, label=labels[i])
    
    # Add threshold line
    ax3.axhline(y=6.0, color='red', linestyle='--', alpha=0.7, label='Shoe Threshold (6.0)')
    
    ax3.set_ylabel('Total Risk Score')
    ax3.set_title('Total Risk Score Comparison')
    ax3.set_xlabel('Time')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Format x-axis
    for ax in [ax1, ax2, ax3]:
        ax.set_xlim(times[0], times[-1])
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.tight_layout()
    plt.savefig('recovery_comparison.png')
    plt.show()

def test_recovery_settings():
    """Test different recovery settings and compare results."""
    test_data = create_test_data()
    
    # Test configs
    configs = [
        # Default settings
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=False,
            enable_time_of_day_factor=False
        ),
        # Graduated recovery
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=True,
            enable_time_of_day_factor=False,
            surface_max_recovery_score=2.0
        ),
        # Time-of-day factor
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=False,
            enable_time_of_day_factor=True
        ),
        # All features
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            enable_graduated_recovery=True,
            enable_time_of_day_factor=True,
            surface_max_recovery_score=2.0
        ),
        # Different surface types
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            surface_type="concrete",
            enable_graduated_recovery=True,
            enable_time_of_day_factor=True
        ),
        RiskConfig(
            surface_recovery_temp_threshold=90.0,
            surface_type="grass",
            enable_graduated_recovery=True,
            enable_time_of_day_factor=True
        ),
    ]
    
    all_results = []
    
    # Test each configuration
    for i, config in enumerate(configs):
        calculator = RiskCalculator(config)
        risk_scores = calculator.calculate_risk_scores(test_data)
        all_results.append(risk_scores)
        
        print(f"\n=== Test Config {i+1} ===")
        print(f"Surface Type: {config.surface_type}")
        print(f"Graduated Recovery: {config.enable_graduated_recovery}")
        print(f"Time-of-Day Factor: {config.enable_time_of_day_factor}")
        
        print("\nHourly Surface Recovery Scores:")
        print("Hour | Temp | Recovery Score")
        print("-" * 30)
        
        for hour, score in enumerate(risk_scores):
            temp = test_data[hour].temperature_f
            time = test_data[hour].datetime.strftime("%H:%M")
            print(f"{time} | {temp:4.1f}°F | {score.surface_recovery_score:5.2f}")
        
        # Show the highest risk hours
        high_risk = [s for s in risk_scores if s.recommend_shoes]
        print(f"\nHigh Risk Hours: {len(high_risk)} out of {len(risk_scores)}")
        if high_risk:
            times = [s.datetime.strftime("%H:%M") for s in high_risk]
            print(f"Times: {', '.join(times)}")
    
    # Visualize comparison
    visualize_results(test_data, all_results)

if __name__ == "__main__":
    print("Testing enhanced surface recovery logic")
    test_recovery_settings() 