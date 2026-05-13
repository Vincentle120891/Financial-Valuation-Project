"""
Statistical Utilities for Financial Historical Data Analysis
Calculates CAGR, Averages, Growth Rates, and Volatility for Step 8 AI Context
"""
import math
from typing import List, Dict, Any, Optional
from app.api.schemas.unified_step_schemas import DataField


def calculate_cagr(start_value: float, end_value: float, periods: int) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate (CAGR)
    Formula: (End/Start)^(1/n) - 1
    """
    if start_value <= 0 or end_value <= 0 or periods <= 0:
        return None
    try:
        return (end_value / start_value) ** (1 / periods) - 1
    except ZeroDivisionError:
        return None


def calculate_average(values: List[float]) -> Optional[float]:
    """Calculate arithmetic mean"""
    if not values:
        return None
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> Optional[float]:
    """Calculate median value"""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return sorted_vals[mid]


def calculate_min_max(values: List[float]) -> Dict[str, Optional[float]]:
    """Calculate min and max values"""
    if not values:
        return {"min": None, "max": None}
    return {"min": min(values), "max": max(values)}


def calculate_volatility(values: List[float]) -> Optional[float]:
    """
    Calculate standard deviation (volatility) of the values
    Uses population standard deviation for historical data
    """
    if len(values) < 2:
        return None
    avg = calculate_average(values)
    if avg is None:
        return None
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def calculate_year_over_year_growth(values: List[float], years: List[int]) -> List[Dict[str, Any]]:
    """
    Calculate Year-over-Year (YoY) growth rates between consecutive periods
    Returns list of {year, growth_rate} dicts
    """
    if len(values) < 2 or len(years) < 2:
        return []

    growth_rates = []
    for i in range(1, len(values)):
        if values[i-1] == 0:
            continue
        growth = (values[i] - values[i-1]) / abs(values[i-1])
        growth_rates.append({
            "year": years[i],
            "growth_rate": growth,
            "previous_value": values[i-1],
            "current_value": values[i]
        })
    return growth_rates


def extract_numeric_values(data_fields: List[DataField]) -> tuple[List[float], List[int]]:
    """
    Extract numeric values and years from a list of DataField objects
    Filters out None values and sorts by year
    """
    values = []
    years = []

    for field in data_fields:
        if field.value is not None and field.year:
            values.append(float(field.value))
            years.append(int(field.year))

    # Sort by year to ensure correct chronological order
    if years:
        sorted_pairs = sorted(zip(years, values))
        years = [y for y, v in sorted_pairs]
        values = [v for y, v in sorted_pairs]

    return values, years


def generate_historical_statistics(data_fields: List[DataField], metric_name: str) -> Dict[str, Any]:
    """
    Generate comprehensive statistics for a historical metric
    Returns a dictionary ready to be injected into AI prompts
    """
    values, years = extract_numeric_values(data_fields)

    if len(values) < 2:
        return {
            "metric": metric_name,
            "available_years": len(values),
            "status": "insufficient_data",
            "message": "Not enough historical data points for statistical analysis"
        }

    # Calculate core statistics
    cagr = None
    if len(values) >= 2:
        periods = years[-1] - years[0]
        if periods > 0:
            cagr = calculate_cagr(values[0], values[-1], periods)

    avg = calculate_average(values)
    median = calculate_median(values)
    min_max = calculate_min_max(values)
    volatility = calculate_volatility(values)
    yoy_growth = calculate_year_over_year_growth(values, years)

    # Calculate average YoY growth
    avg_yoy_growth = None
    if yoy_growth:
        growth_rates = [g["growth_rate"] for g in yoy_growth]
        avg_yoy_growth = calculate_average(growth_rates)

    return {
        "metric": metric_name,
        "available_years": len(values),
        "year_range": f"{years[0]}-{years[-1]}",
        "periods": years[-1] - years[0],
        "latest_value": values[-1],
        "oldest_value": values[0],
        "cagr": cagr,
        "average": avg,
        "median": median,
        "min": min_max["min"],
        "max": min_max["max"],
        "volatility": volatility,
        "average_yoy_growth": avg_yoy_growth,
        "yoy_growth_details": yoy_growth,
        "status": "complete",
        "raw_values": values,
        "raw_years": years
    }