"""Constants used throughout the application."""

# Surface cooling coefficients (slower to faster cooling)
SURFACE_COOLING_COEFFICIENTS = {
    'asphalt': 0.7,    # Slower cooling
    'concrete': 0.85,
    'mixed': 1.0,      # Normal cooling
    'grass': 1.5       # Faster cooling
}

# Night hours definition (7pm to 6am)
NIGHT_START_HOUR = 19  # 7pm
NIGHT_END_HOUR = 6     # 6am

# Time of day cooling multipliers
NIGHT_COOLING_MULTIPLIER = 1.3  # Night cools 30% faster
DAY_COOLING_MULTIPLIER = 1.0    # Standard cooling during day 