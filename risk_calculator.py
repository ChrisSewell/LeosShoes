"""Risk calculation engine for paw burn assessment."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from models import WeatherHour, RiskScore
from config import RiskConfig, get_config
from constants import SURFACE_COOLING_COEFFICIENTS, NIGHT_START_HOUR, NIGHT_END_HOUR
from constants import NIGHT_COOLING_MULTIPLIER, DAY_COOLING_MULTIPLIER

logger = logging.getLogger(__name__)

class RiskCalculator:
    """Calculates paw burn risk scores based on weather conditions."""
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or get_config().risk_config
        
        # Validate surface type is supported
        if self.config.surface_type.lower() not in SURFACE_COOLING_COEFFICIENTS:
            logger.warning(f"Surface type '{self.config.surface_type}' not recognized, using 'mixed' instead")
            self.config.surface_type = "mixed"
            
        # Log enhanced recovery settings
        if self.config.enable_graduated_recovery:
            logger.info(f"Using graduated recovery scoring with max score of {self.config.surface_max_recovery_score}")
        
        if self.config.enable_time_of_day_factor:
            logger.info(f"Time-of-day cooling factor enabled (night: {NIGHT_COOLING_MULTIPLIER}x, day: {DAY_COOLING_MULTIPLIER}x)")
            
        logger.info(f"Surface recovery config: threshold={self.config.surface_recovery_temp_threshold}°F, " 
                  f"hours={self.config.surface_recovery_hours}, surface={self.config.surface_type}")
    
    def calculate_temperature_score(self, temperature_f: float) -> float:
        """Calculate risk score based on air temperature."""
        if temperature_f >= self.config.temp_threshold_high:  # ≥100°F
            return 3.0
        elif temperature_f >= self.config.temp_threshold_med:  # ≥90°F
            return 2.0
        elif temperature_f >= self.config.temp_threshold_low:  # ≥80°F
            return 1.0
        else:
            return 0.0
    
    def calculate_uv_score(self, uv_index: Optional[float]) -> float:
        """Calculate risk score based on UV index."""
        if uv_index is None:
            return 0.0
        
        if uv_index >= self.config.uv_threshold_high:  # ≥10
            return 3.0
        elif uv_index >= self.config.uv_threshold_med:  # ≥8
            return 2.0
        elif uv_index >= self.config.uv_threshold_low:  # ≥6
            return 1.0
        else:
            return 0.0
    
    def calculate_condition_score(self, condition: str) -> float:
        """Calculate risk score based on weather condition."""
        condition_lower = condition.lower()
        if 'sunny' in condition_lower or 'clear' in condition_lower:
            return 1.0
        else:
            return 0.0
    
    def calculate_accumulated_heat_score(self, weather_hours: List[WeatherHour], 
                                       current_index: int) -> float:
        """Calculate risk score based on accumulated heat (rolling average)."""
        if current_index < 1:
            return 0.0
        
        # Get the last N hours (including current)
        window_size = min(self.config.rolling_window_hours, current_index + 1)
        start_index = current_index - window_size + 1
        
        window_hours = weather_hours[start_index:current_index + 1]
        
        # Calculate average temperature and UV
        temp_sum = sum(hour.temperature_f for hour in window_hours)
        avg_temp = temp_sum / len(window_hours)
        
        # Calculate average UV (handling None values)
        uv_values = [hour.uv_index for hour in window_hours if hour.uv_index is not None]
        avg_uv = sum(uv_values) / len(uv_values) if uv_values else 0
        
        # Score based on accumulated heat criteria
        score = 0.0
        if avg_temp > 85.0:
            score += 1.0
        if avg_uv >= 6.0:
            score += 1.0
        
        return min(score, 1.0)  # Cap at 1.0 as per specification
    
    def calculate_surface_recovery_score(self, weather_hours: List[WeatherHour], 
                                       current_index: int) -> float:
        """Calculate surface recovery score with enhanced logic."""
        if current_index < 2:
            return 0.0
        
        # Look back to find the last time temperature was above the threshold
        hours_since_peak = 0
        sun_exposure_hours = 0
        peak_temp = 0
        
        current_hour = weather_hours[current_index].datetime
        
        for i in range(current_index - 1, -1, -1):
            hours_since_peak += 1
            
            # Check if temperature was above recovery threshold
            if weather_hours[i].temperature_f >= self.config.surface_recovery_temp_threshold:
                peak_temp = weather_hours[i].temperature_f
                break
            
            # Count sun exposure during recovery period
            condition = weather_hours[i].condition.lower()
            if 'sunny' in condition or 'clear' in condition:
                sun_exposure_hours += 1
        else:
            # No peak found in available data
            hours_since_peak = current_index + 1
            
        # No recovery needed if no peak was found
        if peak_temp == 0:
            return 0.0
        
        # Apply surface type coefficient
        cooling_coefficient = SURFACE_COOLING_COEFFICIENTS.get(
            self.config.surface_type.lower(), 1.0)
        
        # Apply time-of-day factor if enabled
        if self.config.enable_time_of_day_factor:
            hour_of_day = current_hour.hour
            time_multiplier = (NIGHT_COOLING_MULTIPLIER 
                              if hour_of_day >= NIGHT_START_HOUR or hour_of_day < NIGHT_END_HOUR 
                              else DAY_COOLING_MULTIPLIER)
        else:
            time_multiplier = 1.0
            
        # Calculate sun exposure percentage during recovery
        sun_percentage = sun_exposure_hours / hours_since_peak if hours_since_peak > 0 else 0
        
        # Sun slows cooling (reduce coefficient by up to 30%)
        sun_factor = 1.0 - (sun_percentage * 0.3)
        
        # Final adjusted hours since peak temperature
        adjusted_hours = hours_since_peak * cooling_coefficient * time_multiplier * sun_factor
        
        # Calculate recovery score
        if adjusted_hours <= self.config.surface_recovery_hours:
            # No recovery credit yet
            return 0.0
        elif self.config.enable_graduated_recovery:
            # Graduated recovery (more hours = more recovery credit)
            # Normalize to range 0.0 to max_recovery_score
            hours_over = adjusted_hours - self.config.surface_recovery_hours
            max_additional_hours = self.config.surface_recovery_hours  # Full credit after double the recovery time
            factor = min(1.0, hours_over / max_additional_hours)
            recovery_score = -factor * self.config.surface_max_recovery_score
            
            logger.debug(f"Graduated recovery: {hours_since_peak} hrs since {peak_temp}°F peak, "
                       f"adjusted to {adjusted_hours:.1f} hrs, score: {recovery_score}")
            
            return recovery_score
        else:
            # Original binary approach
            return -1.0
    
    def interpolate_missing_uv(self, weather_hours: List[WeatherHour]) -> List[WeatherHour]:
        """Interpolate missing UV values using nearby hours."""
        if not weather_hours:
            return weather_hours
        
        # Create a copy to avoid modifying the original
        processed_hours = [WeatherHour(
            datetime=hour.datetime,
            temperature_f=hour.temperature_f,
            uv_index=hour.uv_index,
            condition=hour.condition,
            is_forecast=hour.is_forecast
        ) for hour in weather_hours]
        
        # Find UV values that need interpolation
        for i, hour in enumerate(processed_hours):
            if hour.uv_index is None:
                # Look for nearest non-None values
                left_uv = None
                right_uv = None
                
                # Search left
                for j in range(i - 1, -1, -1):
                    if processed_hours[j].uv_index is not None:
                        left_uv = processed_hours[j].uv_index
                        break
                
                # Search right
                for j in range(i + 1, len(processed_hours)):
                    if processed_hours[j].uv_index is not None:
                        right_uv = processed_hours[j].uv_index
                        break
                
                # Interpolate or use fallback
                if left_uv is not None and right_uv is not None:
                    processed_hours[i].uv_index = (left_uv + right_uv) / 2
                elif left_uv is not None:
                    processed_hours[i].uv_index = left_uv
                elif right_uv is not None:
                    processed_hours[i].uv_index = right_uv
                else:
                    # Use temperature-based fallback (rough approximation)
                    temp_f = hour.temperature_f
                    if temp_f >= 95:
                        processed_hours[i].uv_index = 8.0
                    elif temp_f >= 85:
                        processed_hours[i].uv_index = 6.0
                    elif temp_f >= 75:
                        processed_hours[i].uv_index = 4.0
                    else:
                        processed_hours[i].uv_index = 2.0
        
        return processed_hours
    
    def detect_rapid_heat_swings(self, weather_hours: List[WeatherHour]) -> List[int]:
        """Detect hours with rapid temperature changes."""
        rapid_swing_indices = []
        
        for i in range(1, len(weather_hours)):
            temp_diff = abs(weather_hours[i].temperature_f - weather_hours[i-1].temperature_f)
            if temp_diff >= 15.0:  # 15°F+ change in one hour
                rapid_swing_indices.append(i)
                logger.warning(f"Rapid temperature swing detected at {weather_hours[i].datetime}: "
                             f"{temp_diff:.1f}°F change")
        
        return rapid_swing_indices
    
    def calculate_risk_scores(self, weather_hours: List[WeatherHour]) -> List[RiskScore]:
        """Calculate risk scores for all weather hours."""
        if not weather_hours:
            return []
        
        # Preprocess data
        processed_hours = self.interpolate_missing_uv(weather_hours)
        rapid_swings = self.detect_rapid_heat_swings(processed_hours)
        
        risk_scores = []
        
        for i, hour in enumerate(processed_hours):
            # Calculate individual component scores
            temp_score = self.calculate_temperature_score(hour.temperature_f)
            uv_score = self.calculate_uv_score(hour.uv_index)
            condition_score = self.calculate_condition_score(hour.condition)
            accumulated_score = self.calculate_accumulated_heat_score(processed_hours, i)
            recovery_score = self.calculate_surface_recovery_score(processed_hours, i)
            
            # Apply rapid swing bonus
            rapid_swing_bonus = 0.5 if i in rapid_swings else 0.0
            
            # Calculate total score
            total_score = (temp_score + uv_score + condition_score + 
                          accumulated_score + recovery_score + rapid_swing_bonus)
            
            # Ensure score is within bounds
            total_score = max(0.0, min(10.0, total_score))
            
            # Determine if shoes are recommended
            recommend_shoes = total_score >= self.config.risk_threshold_shoes
            
            risk_scores.append(RiskScore(
                datetime=hour.datetime,
                temperature_score=temp_score,
                uv_score=uv_score,
                condition_score=condition_score,
                accumulated_heat_score=accumulated_score,
                surface_recovery_score=recovery_score,
                total_score=total_score,
                recommend_shoes=recommend_shoes
            ))
        
        return risk_scores
    
    def identify_continuous_risk_blocks(self, risk_scores: List[RiskScore]) -> List[Tuple[datetime, datetime]]:
        """Identify continuous time blocks where shoes are recommended."""
        if not risk_scores:
            return []
        
        blocks = []
        current_block_start = None
        
        for score in risk_scores:
            if score.recommend_shoes:
                if current_block_start is None:
                    current_block_start = score.datetime
            else:
                if current_block_start is not None:
                    blocks.append((current_block_start, score.datetime))
                    current_block_start = None
        
        # Handle case where risk period extends to the end
        if current_block_start is not None:
            blocks.append((current_block_start, risk_scores[-1].datetime))
        
        return blocks
    
    def generate_recommendations(self, risk_scores: List[RiskScore]) -> dict:
        """Generate comprehensive recommendations based on risk scores."""
        if not risk_scores:
            return {"error": "No risk data available"}
        
        # Calculate statistics
        total_hours = len(risk_scores)
        high_risk_hours = sum(1 for score in risk_scores if score.recommend_shoes)
        max_score = max(score.total_score for score in risk_scores)
        avg_score = sum(score.total_score for score in risk_scores) / total_hours
        
        # Find peak risk time
        peak_score = max(risk_scores, key=lambda x: x.total_score)
        
        # Identify continuous risk blocks
        risk_blocks = self.identify_continuous_risk_blocks(risk_scores)
        
        recommendations = {
            "summary": {
                "total_hours_analyzed": total_hours,
                "high_risk_hours": high_risk_hours,
                "max_risk_score": round(max_score, 1),
                "average_risk_score": round(avg_score, 1),
                "peak_risk_time": peak_score.datetime.strftime("%H:%M"),
                "continuous_risk_blocks": len(risk_blocks)
            },
            "risk_periods": [
                {
                    "start": start.strftime("%H:%M"),
                    "end": end.strftime("%H:%M"),
                    "duration_hours": round((end - start).total_seconds() / 3600, 1)
                }
                for start, end in risk_blocks
            ],
            "recommendations": []
        }
        
        # Generate specific recommendations
        if high_risk_hours == 0:
            recommendations["recommendations"].append(
                "🐾 Great news! No protective footwear needed today - paws should be safe on all surfaces."
            )
        else:
            recommendations["recommendations"].append(
                f"⚠️  Protective dog shoes recommended for {high_risk_hours} hours today."
            )
            
            if risk_blocks:
                recommendations["recommendations"].append(
                    "🕐 Avoid walks during the identified high-risk time periods, or ensure your dog wears protective booties."
                )
            
            if max_score >= 8:
                recommendations["recommendations"].append(
                    "🔥 EXTREME RISK: Surface temperatures may cause immediate paw burns. Keep walks very short and on grass/shaded areas only."
                )
            elif max_score >= 7:
                recommendations["recommendations"].append(
                    "🌡️  HIGH RISK: Hot surfaces likely. Test pavement with your hand - if too hot for 5 seconds, it's too hot for paws."
                )
        
        return recommendations

def create_risk_calculator(config: Optional[RiskConfig] = None) -> RiskCalculator:
    """Create a risk calculator with optional custom configuration."""
    return RiskCalculator(config) 