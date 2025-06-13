"""Plotting and visualization for paw burn risk assessment."""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
import warnings
import os
import shutil
from models import WeatherHour, RiskScore
from config import RiskConfig, get_config

# Suppress matplotlib UserWarnings and macOS GUI warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', message='.*NSSavePanel.*')

class RiskPlotter:
    """Handles plotting and visualization of risk data."""
    
    def __init__(self, figure_size: Tuple[int, int] = (12, 8), use_24hr_time: Optional[bool] = None):
        self.figure_size = figure_size
        self.plots_dir = "plots"
        self._plots_dir_setup = False
        
        # Get time format preference from config if not specified
        if use_24hr_time is None:
            config = get_config().risk_config
            self.use_24hr_time = getattr(config, 'use_24hr_time', False)
        else:
            self.use_24hr_time = use_24hr_time
        
        # Set up matplotlib style and suppress warnings
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = figure_size
        plt.rcParams['font.size'] = 10
    
    def get_time_formatter(self):
        """Get the appropriate time formatter based on config."""
        if self.use_24hr_time:
            return mdates.DateFormatter('%H:%M')
        else:
            return mdates.DateFormatter('%I:%M %p')
    
    def _setup_plots_directory(self):
        """Create and clear plots directory."""
        if os.path.exists(self.plots_dir):
            # Clear existing plots
            shutil.rmtree(self.plots_dir)
        os.makedirs(self.plots_dir, exist_ok=True)
        print(f"📁 Plots directory ready: {self.plots_dir}/")
    
    def _safe_save_plot(self, filename: str, dpi: int = 300):
        """Safely save plot to plots directory."""
        if filename:
            # Setup plots directory on first save
            if not self._plots_dir_setup:
                self._setup_plots_directory()
                self._plots_dir_setup = True
            
            # Create full path in plots directory
            save_path = os.path.join(self.plots_dir, filename)
            
            # Save with current backend (don't switch backends as it causes blank files)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                plt.savefig(save_path, dpi=dpi, bbox_inches='tight', facecolor='white')
            
            print(f"📊 Plot saved: {save_path}")
    
    def plot_risk_timeline(self, risk_scores: List[RiskScore], 
                          weather_hours: List[WeatherHour], 
                          threshold: float = 6.0,
                          save_path: Optional[str] = None,
                          show: bool = True) -> None:
        """Plot risk scores over time with recommendation threshold."""
        if not risk_scores:
            print("No risk data to plot")
            return
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=self.figure_size, 
                                           sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
        
        # Extract data
        times = [score.datetime for score in risk_scores]
        total_scores = [score.total_score for score in risk_scores]
        temperatures = [hour.temperature_f for hour in weather_hours]
        uv_indices = [hour.uv_index or 0 for hour in weather_hours]
        
        # Main risk score plot
        ax1.plot(times, total_scores, 'b-', linewidth=2, label='Risk Score')
        ax1.axhline(y=threshold, color='red', linestyle='--', alpha=0.7, 
                   label=f'Shoe Threshold ({threshold})')
        
        # Highlight high-risk periods
        high_risk_times = []
        high_risk_scores = []
        for score in risk_scores:
            if score.recommend_shoes:
                high_risk_times.append(score.datetime)
                high_risk_scores.append(score.total_score)
        
        if high_risk_times:
            ax1.scatter(high_risk_times, high_risk_scores, color='red', s=50, 
                       alpha=0.7, zorder=5, label='Shoes Recommended')
        
        ax1.set_ylabel('Risk Score')
        ax1.set_title('Paw Burn Risk Assessment Timeline')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 10)
        
        # Temperature subplot
        ax2.plot(times, temperatures, 'orange', linewidth=2, label='Temperature (°F)')
        ax2.axhline(y=80, color='yellow', linestyle=':', alpha=0.7, label='80°F')
        ax2.axhline(y=90, color='orange', linestyle=':', alpha=0.7, label='90°F')
        ax2.axhline(y=100, color='red', linestyle=':', alpha=0.7, label='100°F')
        ax2.set_ylabel('Temperature (°F)')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        # UV Index subplot
        ax3.plot(times, uv_indices, 'purple', linewidth=2, label='UV Index')
        ax3.axhline(y=6, color='yellow', linestyle=':', alpha=0.7, label='UV 6')
        ax3.axhline(y=8, color='orange', linestyle=':', alpha=0.7, label='UV 8')
        ax3.axhline(y=10, color='red', linestyle=':', alpha=0.7, label='UV 10')
        ax3.set_ylabel('UV Index')
        ax3.set_xlabel('Time')
        ax3.legend(loc='upper right')
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis
        time_formatter = self.get_time_formatter()
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(time_formatter)
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                plt.tight_layout()
            except:
                # If tight_layout fails, adjust manually
                plt.subplots_adjust(hspace=0.4, bottom=0.15)
        
        if save_path:
            self._safe_save_plot(save_path)
        
        if show:
            plt.show()
    
    def plot_risk_components(self, risk_scores: List[RiskScore], 
                           save_path: Optional[str] = None,
                           show: bool = True) -> None:
        """Plot breakdown of risk score components."""
        if not risk_scores:
            print("No risk data to plot")
            return
        
        fig, ax = plt.subplots(figsize=self.figure_size)
        
        # Extract data
        times = [score.datetime for score in risk_scores]
        temp_scores = [score.temperature_score for score in risk_scores]
        uv_scores = [score.uv_score for score in risk_scores]
        condition_scores = [score.condition_score for score in risk_scores]
        accumulated_scores = [score.accumulated_heat_score for score in risk_scores]
        recovery_scores = [score.surface_recovery_score for score in risk_scores]
        
        # Create stacked area plot
        ax.stackplot(times, temp_scores, uv_scores, condition_scores, 
                    accumulated_scores, recovery_scores,
                    labels=['Temperature', 'UV Index', 'Condition', 'Accumulated Heat', 'Surface Recovery'],
                    alpha=0.7)
        
        ax.set_ylabel('Risk Score Components')
        ax.set_xlabel('Time')
        ax.set_title('Risk Score Component Breakdown')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        time_formatter = self.get_time_formatter()
        ax.xaxis.set_major_formatter(time_formatter)
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                plt.tight_layout()
            except:
                # If tight_layout fails, adjust manually
                plt.subplots_adjust(right=0.75, bottom=0.15)
        
        if save_path:
            self._safe_save_plot(save_path)
            print(f"Component plot saved")
        
        if show:
            plt.show()
    
    def plot_risk_heatmap(self, risk_scores: List[RiskScore], 
                         save_path: Optional[str] = None,
                         show: bool = True) -> None:
        """Create a heatmap visualization of risk throughout the day."""
        if not risk_scores:
            print("No risk data to plot")
            return
        
        fig, ax = plt.subplots(figsize=(12, 3))
        
        # Create time vs risk matrix
        hours = [score.datetime.hour for score in risk_scores]
        scores = [score.total_score for score in risk_scores]
        
        # Create a matrix for the heatmap
        hour_range = list(range(24))
        risk_matrix = np.zeros((1, 24))
        
        for hour, score in zip(hours, scores):
            risk_matrix[0, hour] = score
        
        # Create heatmap
        im = ax.imshow(risk_matrix, cmap='RdYlBu_r', aspect='auto', vmin=0, vmax=10)
        
        # Customize the plot
        ax.set_xticks(range(24))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(24)])
        ax.set_yticks([])
        ax.set_xlabel('Hour of Day')
        ax.set_title('Paw Burn Risk Heatmap')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='horizontal', pad=0.1)
        cbar.set_label('Risk Score')
        
        # Add threshold line
        threshold_line = 6.0 / 10.0  # Normalize to colormap scale
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                plt.tight_layout()
            except:
                # If tight_layout fails, adjust manually
                plt.subplots_adjust(bottom=0.2)
        
        if save_path:
            self._safe_save_plot(save_path)
            print(f"Heatmap saved")
        
        if show:
            plt.show()
    
    def create_summary_dashboard(self, risk_scores: List[RiskScore], 
                               weather_hours: List[WeatherHour],
                               recommendations: dict,
                               save_path: Optional[str] = None,
                               show: bool = True) -> None:
        """Create a comprehensive dashboard with all visualizations."""
        if not risk_scores or not weather_hours:
            print("Insufficient data for dashboard")
            return
        
        fig = plt.figure(figsize=(16, 12))
        
        # Create subplots
        gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.3)
        
        # Main timeline plot
        ax1 = fig.add_subplot(gs[0, :])
        times = [score.datetime for score in risk_scores]
        total_scores = [score.total_score for score in risk_scores]
        
        ax1.plot(times, total_scores, 'b-', linewidth=3, label='Risk Score')
        ax1.axhline(y=6, color='red', linestyle='--', alpha=0.7, label='Shoe Threshold')
        
        # Highlight high-risk periods
        high_risk_periods = []
        current_start = None
        
        for i, score in enumerate(risk_scores):
            if score.recommend_shoes and current_start is None:
                current_start = i
            elif not score.recommend_shoes and current_start is not None:
                high_risk_periods.append((current_start, i))
                current_start = None
        
        if current_start is not None:
            high_risk_periods.append((current_start, len(risk_scores)))
        
        for start_idx, end_idx in high_risk_periods:
            ax1.axvspan(times[start_idx], times[end_idx-1], alpha=0.3, color='red')
        
        ax1.set_ylabel('Risk Score')
        ax1.set_title('Paw Burn Risk Assessment - Daily Overview')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 10)
        
        # Component breakdown
        ax2 = fig.add_subplot(gs[1, 0])
        component_names = ['Temp', 'UV', 'Condition', 'Heat Accum', 'Recovery']
        avg_components = [
            np.mean([s.temperature_score for s in risk_scores]),
            np.mean([s.uv_score for s in risk_scores]),
            np.mean([s.condition_score for s in risk_scores]),
            np.mean([s.accumulated_heat_score for s in risk_scores]),
            np.mean([s.surface_recovery_score for s in risk_scores])
        ]
        
        bars = ax2.bar(component_names, avg_components, color=['orange', 'purple', 'lightblue', 'yellow', 'green'])
        ax2.set_ylabel('Average Score')
        ax2.set_title('Average Risk Components')
        ax2.tick_params(axis='x', rotation=45)
        
        # Statistics
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.axis('off')
        
        stats_text = f"""
        DAILY SUMMARY
        
        Total Hours Analyzed: {recommendations['summary']['total_hours_analyzed']}
        High Risk Hours: {recommendations['summary']['high_risk_hours']}
        Max Risk Score: {recommendations['summary']['max_risk_score']}
        Average Risk Score: {recommendations['summary']['average_risk_score']}
        Peak Risk Time: {recommendations['summary']['peak_risk_time']}
        Risk Periods: {recommendations['summary']['continuous_risk_blocks']}
        """
        
        ax3.text(0.1, 0.9, stats_text, transform=ax3.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace')
        
        # Weather conditions
        ax4 = fig.add_subplot(gs[2, :])
        temperatures = [hour.temperature_f for hour in weather_hours]
        uv_indices = [hour.uv_index or 0 for hour in weather_hours]
        
        ax4_twin = ax4.twinx()
        
        line1 = ax4.plot(times, temperatures, 'orange', linewidth=2, label='Temperature (°F)')
        line2 = ax4_twin.plot(times, uv_indices, 'purple', linewidth=2, label='UV Index')
        
        ax4.set_ylabel('Temperature (°F)', color='orange')
        ax4_twin.set_ylabel('UV Index', color='purple')
        ax4.set_xlabel('Time')
        ax4.set_title('Weather Conditions')
        
        # Format x-axis for all subplots
        time_formatter = self.get_time_formatter()
        for ax in [ax1, ax4]:
            ax.xaxis.set_major_formatter(time_formatter)
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Use constrained layout or manual adjustment instead of tight_layout
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            try:
                plt.tight_layout()
            except:
                # If tight_layout fails with complex layouts, adjust manually
                plt.subplots_adjust(hspace=0.4, wspace=0.4, bottom=0.1, top=0.95)
        
        if save_path:
            self._safe_save_plot(save_path)
            print(f"Dashboard saved")
        
        if show:
            plt.show()

def create_plotter(figure_size: Tuple[int, int] = (12, 8)) -> RiskPlotter:
    """Create a risk plotter with specified figure size."""
    return RiskPlotter(figure_size) 