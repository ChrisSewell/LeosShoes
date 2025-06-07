"""Main application for paw burn risk assessment."""

import logging
import argparse
from datetime import datetime, timedelta
from typing import Optional
import json

from config import get_config, AppConfig
from models import DatabaseManager
from weather_api import create_weather_client
from risk_calculator import create_risk_calculator
from plotting import create_plotter

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PawRiskApp:
    """Main application class for paw burn risk assessment."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.db_manager = DatabaseManager(self.config.database_path)
        self.weather_client = create_weather_client()
        self.risk_calculator = create_risk_calculator()
        self.plotter = create_plotter()
    
    def fetch_and_analyze_today(self, location: Optional[str] = None) -> dict:
        """Fetch weather data and analyze risk for today."""
        location = location or self.config.default_location
        
        print(f"🌤️  Fetching weather data for {location}...")
        
        try:
            # Fetch complete day weather data
            weather_hours = self.weather_client.get_full_day_weather(location)
            
            if not weather_hours:
                return {"error": "No weather data available"}
            
            print(f"📊 Retrieved {len(weather_hours)} hours of weather data")
            
            # Save weather data to database
            self.db_manager.save_weather_data(weather_hours)
            
            # Calculate risk scores
            print("🧮 Calculating paw burn risk scores...")
            risk_scores = self.risk_calculator.calculate_risk_scores(weather_hours)
            
            if not risk_scores:
                return {"error": "Unable to calculate risk scores"}
            
            # Save risk scores to database
            self.db_manager.save_risk_scores(risk_scores)
            
            # Generate recommendations
            recommendations = self.risk_calculator.generate_recommendations(risk_scores)
            
            return {
                "weather_hours": weather_hours,
                "risk_scores": risk_scores,
                "recommendations": recommendations,
                "location": location
            }
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return {"error": str(e)}
    
    def print_summary(self, analysis_result: dict):
        """Print a formatted summary of the analysis."""
        if "error" in analysis_result:
            print(f"❌ Error: {analysis_result['error']}")
            return
        
        recommendations = analysis_result["recommendations"]
        location = analysis_result["location"]
        
        print("\n" + "="*60)
        print(f"🐕 PAW BURN RISK ASSESSMENT - {location.upper()}")
        print("="*60)
        
        # Summary statistics
        summary = recommendations["summary"]
        print(f"\n📈 DAILY SUMMARY:")
        print(f"   • Total Hours Analyzed: {summary['total_hours_analyzed']}")
        print(f"   • High Risk Hours: {summary['high_risk_hours']}")
        print(f"   • Maximum Risk Score: {summary['max_risk_score']}/10")
        print(f"   • Average Risk Score: {summary['average_risk_score']}/10")
        print(f"   • Peak Risk Time: {summary['peak_risk_time']}")
        print(f"   • Continuous Risk Periods: {summary['continuous_risk_blocks']}")
        
        # Risk periods
        if recommendations["risk_periods"]:
            print(f"\n⏰ HIGH RISK TIME PERIODS:")
            for period in recommendations["risk_periods"]:
                print(f"   • {period['start']} - {period['end']} ({period['duration_hours']} hours)")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in recommendations["recommendations"]:
            print(f"   {rec}")
        
        print("\n" + "="*60)
    
    def print_detailed_hourly(self, analysis_result: dict):
        """Print detailed hourly breakdown."""
        if "error" in analysis_result:
            return
        
        weather_hours = analysis_result["weather_hours"]
        risk_scores = analysis_result["risk_scores"]
        
        print("\n🕐 HOURLY BREAKDOWN:")
        print("-" * 80)
        print(f"{'Time':>6} {'Temp':>6} {'UV':>4} {'Condition':>12} {'Risk':>6} {'Shoes':>7}")
        print("-" * 80)
        
        for weather, risk in zip(weather_hours, risk_scores):
            time_str = weather.datetime.strftime("%H:%M")
            temp_str = f"{weather.temperature_f:.0f}°F"
            uv_str = f"{weather.uv_index:.1f}" if weather.uv_index else "N/A"
            condition_short = weather.condition[:12]
            risk_str = f"{risk.total_score:.1f}"
            shoes_str = "YES" if risk.recommend_shoes else "no"
            shoes_color = "⚠️ " if risk.recommend_shoes else "✅ "
            
            print(f"{time_str:>6} {temp_str:>6} {uv_str:>4} {condition_short:>12} "
                  f"{risk_str:>6} {shoes_color}{shoes_str:>5}")
    
    def create_plots(self, analysis_result: dict, save_plots: bool = False):
        """Create and display plots."""
        if "error" in analysis_result:
            return
        
        weather_hours = analysis_result["weather_hours"]
        risk_scores = analysis_result["risk_scores"]
        recommendations = analysis_result["recommendations"]
        location = analysis_result["location"]
        
        if save_plots:
            print("\n📊 Generating and saving visualizations...")
        else:
            print("\n📊 Generating visualizations...")
        
        # Create timestamp for file names
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        location_safe = location.replace(" ", "_").replace(",", "")
        
        try:
            # Main risk timeline
            save_path = f"risk_timeline_{location_safe}_{timestamp}.png" if save_plots else None
            self.plotter.plot_risk_timeline(
                risk_scores, weather_hours, 
                threshold=self.config.risk_config.risk_threshold_shoes,
                save_path=save_path,
                show=not save_plots
            )
            
            # Component breakdown
            save_path = f"risk_components_{location_safe}_{timestamp}.png" if save_plots else None
            self.plotter.plot_risk_components(
                risk_scores,
                save_path=save_path,
                show=not save_plots
            )
            
            # Summary dashboard
            save_path = f"risk_dashboard_{location_safe}_{timestamp}.png" if save_plots else None
            self.plotter.create_summary_dashboard(
                risk_scores, weather_hours, recommendations,
                save_path=save_path,
                show=not save_plots
            )
            
        except Exception as e:
            logger.error(f"Error creating plots: {e}")
            print(f"⚠️  Error creating plots: {e}")

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Paw Burn Risk Assessment Tool")
    parser.add_argument("--location", "-l", type=str, help="Location for weather data (city name, zip code, or coordinates)")
    parser.add_argument("--detailed", "-d", action="store_true", help="Show detailed hourly breakdown")
    parser.add_argument("--plot", "-p", action="store_true", help="Show plots")
    parser.add_argument("--save-plots", "-s", action="store_true", help="Save plots to files")
    parser.add_argument("--no-recommendations", action="store_true", help="Skip recommendations")
    parser.add_argument("--config-check", action="store_true", help="Check configuration and exit")
    
    args = parser.parse_args()
    
    try:
        # Initialize application
        print("🐾 Paw Burn Risk Assessment Tool")
        print("=" * 40)
        
        # Check configuration if requested
        if args.config_check:
            try:
                config = get_config()
                print("✅ Configuration loaded successfully")
                print(f"API Key: {'Set' if config.weather_api_key else 'NOT SET'}")
                print(f"Default Location: {config.default_location}")
                print(f"Database Path: {config.database_path}")
                print(f"Risk Threshold: {config.risk_config.risk_threshold_shoes}")
                return
            except Exception as e:
                print(f"❌ Configuration error: {e}")
                return
        
        app = PawRiskApp()
        
        # Run analysis
        analysis_result = app.fetch_and_analyze_today(args.location)
        
        # Display results
        if args.detailed:
            app.print_detailed_hourly(analysis_result)
        
        if args.plot or args.save_plots:
            app.create_plots(analysis_result, save_plots=args.save_plots)
        
        # Show summary unless explicitly disabled
        if not args.no_recommendations:
            app.print_summary(analysis_result)
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")

if __name__ == "__main__":
    main() 