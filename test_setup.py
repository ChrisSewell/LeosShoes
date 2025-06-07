"""Test script to verify setup and configuration."""

import sys
import os
from datetime import datetime

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        import requests
        print("✅ requests")
    except ImportError:
        print("❌ requests - run: pip install requests")
        return False
    
    try:
        import matplotlib
        print("✅ matplotlib")
    except ImportError:
        print("❌ matplotlib - run: pip install matplotlib")
        return False
    
    try:
        import pandas
        print("✅ pandas")
    except ImportError:
        print("❌ pandas - run: pip install pandas")
        return False
    
    try:
        import numpy
        print("✅ numpy")
    except ImportError:
        print("❌ numpy - run: pip install numpy")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv - run: pip install python-dotenv")
        return False
    
    return True

def test_local_modules():
    """Test that local modules can be imported."""
    print("\n🔍 Testing local modules...")
    
    try:
        from config import get_config
        print("✅ config.py")
    except ImportError as e:
        print(f"❌ config.py - {e}")
        return False
    
    try:
        from models import WeatherHour, RiskScore, DatabaseManager
        print("✅ models.py")
    except ImportError as e:
        print(f"❌ models.py - {e}")
        return False
    
    try:
        from weather_api import WeatherAPIClient
        print("✅ weather_api.py")
    except ImportError as e:
        print(f"❌ weather_api.py - {e}")
        return False
    
    try:
        from risk_calculator import RiskCalculator
        print("✅ risk_calculator.py")
    except ImportError as e:
        print(f"❌ risk_calculator.py - {e}")
        return False
    
    try:
        from plotting import RiskPlotter
        print("✅ plotting.py")
    except ImportError as e:
        print(f"❌ plotting.py - {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")
    
    # Check for .env file
    if not os.path.exists('.env'):
        print("⚠️  No .env file found")
        print("   Create one from env_template.txt:")
        print("   cp env_template.txt .env")
        print("   Then edit .env with your WeatherAPI key")
        return False
    
    try:
        from config import get_config
        config = get_config()
        
        if not config.weather_api_key or config.weather_api_key == "your_weatherapi_key_here":
            print("❌ WeatherAPI key not set")
            print("   Edit your .env file and add your API key:")
            print("   WEATHER_API_KEY=your_actual_key_here")
            return False
        else:
            print("✅ WeatherAPI key configured")
        
        print(f"✅ Default location: {config.default_location}")
        print(f"✅ Database path: {config.database_path}")
        print(f"✅ Risk threshold: {config.risk_config.risk_threshold_shoes}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_database():
    """Test database initialization."""
    print("\n🔍 Testing database...")
    
    try:
        from models import DatabaseManager
        db = DatabaseManager("test_db.db")
        print("✅ Database initialization successful")
        
        # Clean up test database
        os.remove("test_db.db")
        print("✅ Database cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_weather_api():
    """Test weather API connection."""
    print("\n🔍 Testing WeatherAPI connection...")
    
    try:
        from weather_api import create_weather_client
        client = create_weather_client()
        
        # Test with multiple location formats
        test_locations = ["London", "10001"]  # City and zip code
        
        for location in test_locations:
            if client.validate_location(location):
                print(f"✅ WeatherAPI connection successful (tested with {location})")
                return True
        
        print("❌ WeatherAPI validation failed for all test locations")
        return False
        
    except Exception as e:
        print(f"❌ WeatherAPI error: {e}")
        print("   Check your API key and internet connection")
        return False

def main():
    """Run all tests."""
    print("🐾 Paw Burn Risk Assessment - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Import Dependencies", test_imports),
        ("Local Modules", test_local_modules),
        ("Configuration", test_configuration),
        ("Database", test_database),
        ("WeatherAPI", test_weather_api),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nTry running:")
        print("  python main.py --config-check")
        print("  python main.py --location 'Your City'")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nFor help, check:")
        print("  - README.md for setup instructions")
        print("  - env_template.txt for configuration")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 