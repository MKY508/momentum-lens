"""
Input validation utilities for the Momentum Lens system.
"""

import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import pandas as pd
import logging

from backend.config.config import get_config_manager

logger = logging.getLogger(__name__)


def validate_etf_code(code: str) -> bool:
    """
    Validate ETF code format
    
    Args:
        code: ETF code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not code or not isinstance(code, str):
        return False
    
    # Chinese ETF codes are 6 digits
    pattern = r'^[0-9]{6}$'
    
    if not re.match(pattern, code):
        return False
    
    # Shanghai ETFs start with 5
    # Shenzhen ETFs start with 1
    first_digit = code[0]
    if first_digit not in ['1', '5']:
        return False
    
    return True


def validate_price_data(data: Union[pd.DataFrame, Dict]) -> tuple[bool, str]:
    """
    Validate price data format and content
    
    Args:
        data: Price data to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(data, pd.DataFrame):
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        # Check for empty DataFrame
        if data.empty:
            return False, "Price data is empty"
        
        # Validate price relationships
        invalid_rows = []
        for idx, row in data.iterrows():
            if row['high'] < row['low']:
                invalid_rows.append(idx)
            if row['high'] < row['open'] or row['high'] < row['close']:
                invalid_rows.append(idx)
            if row['low'] > row['open'] or row['low'] > row['close']:
                invalid_rows.append(idx)
            if row['volume'] < 0:
                invalid_rows.append(idx)
        
        if invalid_rows:
            return False, f"Invalid price relationships at rows: {invalid_rows[:5]}..."
        
    elif isinstance(data, dict):
        # Validate dictionary format
        required_keys = ['open', 'high', 'low', 'close', 'volume']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"
        
        # Validate values
        try:
            open_price = float(data['open'])
            high_price = float(data['high'])
            low_price = float(data['low'])
            close_price = float(data['close'])
            volume = float(data['volume'])
            
            if high_price < low_price:
                return False, "High price cannot be less than low price"
            if high_price < open_price or high_price < close_price:
                return False, "High price must be >= open and close prices"
            if low_price > open_price or low_price > close_price:
                return False, "Low price must be <= open and close prices"
            if volume < 0:
                return False, "Volume cannot be negative"
            
        except (ValueError, TypeError) as e:
            return False, f"Invalid price values: {e}"
    
    else:
        return False, "Data must be a DataFrame or dictionary"
    
    return True, ""


def validate_parameters(params: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate trading parameters
    
    Args:
        params: Parameters dictionary to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    # Validate stop loss parameters
    if 'stop_loss_min' in params:
        value = params['stop_loss_min']
        if not isinstance(value, (int, float)):
            errors.append("stop_loss_min must be a number")
        elif value > -0.05 or value < -0.30:
            errors.append("stop_loss_min must be between -30% and -5%")
    
    if 'stop_loss_max' in params:
        value = params['stop_loss_max']
        if not isinstance(value, (int, float)):
            errors.append("stop_loss_max must be a number")
        elif value > -0.05 or value < -0.30:
            errors.append("stop_loss_max must be between -30% and -5%")
    
    # Validate buffer zone
    if 'buffer_zone_min' in params:
        value = params['buffer_zone_min']
        if not isinstance(value, (int, float)):
            errors.append("buffer_zone_min must be a number")
        elif value < 0.01 or value > 0.10:
            errors.append("buffer_zone_min must be between 1% and 10%")
    
    # Validate holding period
    if 'min_holding_days' in params:
        value = params['min_holding_days']
        if not isinstance(value, int):
            errors.append("min_holding_days must be an integer")
        elif value < 1 or value > 365:
            errors.append("min_holding_days must be between 1 and 365")
    
    # Validate correlation limit
    if 'correlation_limit' in params:
        value = params['correlation_limit']
        if not isinstance(value, (int, float)):
            errors.append("correlation_limit must be a number")
        elif value < 0 or value > 1:
            errors.append("correlation_limit must be between 0 and 1")
    
    # Validate weights
    if 'core_target_weight' in params and 'satellite_target_weight' in params:
        core = params['core_target_weight']
        satellite = params['satellite_target_weight']
        
        if not isinstance(core, (int, float)) or not isinstance(satellite, (int, float)):
            errors.append("Portfolio weights must be numbers")
        elif abs((core + satellite) - 1.0) > 0.05:  # Allow 5% cash buffer
            errors.append("Core + Satellite weights should sum to approximately 1.0")
    
    return len(errors) == 0, errors


def validate_orders(orders: List[Dict]) -> tuple[bool, List[str]]:
    """
    Validate order list
    
    Args:
        orders: List of order dictionaries
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    for i, order in enumerate(orders):
        # Check required fields
        required_fields = ['code', 'side', 'quantity', 'order_type']
        missing_fields = [field for field in required_fields if field not in order]
        
        if missing_fields:
            errors.append(f"Order {i}: Missing fields {missing_fields}")
            continue
        
        # Validate ETF code
        if not validate_etf_code(order['code']):
            errors.append(f"Order {i}: Invalid ETF code {order['code']}")
        
        # Validate side
        if order['side'] not in ['BUY', 'SELL']:
            errors.append(f"Order {i}: Side must be BUY or SELL")
        
        # Validate quantity
        try:
            quantity = float(order['quantity'])
            if quantity <= 0:
                errors.append(f"Order {i}: Quantity must be positive")
            # Check lot size (Chinese markets typically 100 shares)
            if quantity % 100 != 0:
                errors.append(f"Order {i}: Quantity must be in multiples of 100")
        except (ValueError, TypeError):
            errors.append(f"Order {i}: Invalid quantity value")
        
        # Validate order type
        if order['order_type'] not in ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT']:
            errors.append(f"Order {i}: Invalid order type")
        
        # Validate limit price for limit orders
        if order['order_type'] in ['LIMIT', 'STOP_LIMIT']:
            if 'limit_price' not in order:
                errors.append(f"Order {i}: Limit price required for {order['order_type']} order")
            else:
                try:
                    limit_price = float(order['limit_price'])
                    if limit_price <= 0:
                        errors.append(f"Order {i}: Limit price must be positive")
                except (ValueError, TypeError):
                    errors.append(f"Order {i}: Invalid limit price")
        
        # Validate stop price for stop orders
        if order['order_type'] in ['STOP', 'STOP_LIMIT']:
            if 'stop_price' not in order:
                errors.append(f"Order {i}: Stop price required for {order['order_type']} order")
            else:
                try:
                    stop_price = float(order['stop_price'])
                    if stop_price <= 0:
                        errors.append(f"Order {i}: Stop price must be positive")
                except (ValueError, TypeError):
                    errors.append(f"Order {i}: Invalid stop price")
    
    return len(errors) == 0, errors


def validate_date_range(start_date: Any, end_date: Any) -> tuple[bool, str]:
    """
    Validate date range
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Convert to date objects if necessary
    try:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()
        elif not isinstance(start_date, date):
            return False, "Invalid start_date format"
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        elif isinstance(end_date, datetime):
            end_date = end_date.date()
        elif not isinstance(end_date, date):
            return False, "Invalid end_date format"
        
    except ValueError as e:
        return False, f"Date parsing error: {e}"
    
    # Validate range
    if start_date > end_date:
        return False, "Start date must be before or equal to end date"
    
    if end_date > date.today():
        return False, "End date cannot be in the future"
    
    # Check reasonable range (e.g., max 10 years)
    if (end_date - start_date).days > 3650:
        return False, "Date range exceeds maximum of 10 years"
    
    return True, ""


def validate_portfolio_weights(weights: Dict[str, float]) -> tuple[bool, str]:
    """
    Validate portfolio weights
    
    Args:
        weights: Dictionary of {etf_code: weight}
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not weights:
        return False, "Weights dictionary is empty"
    
    # Check each weight
    for code, weight in weights.items():
        if not validate_etf_code(code):
            return False, f"Invalid ETF code: {code}"
        
        if not isinstance(weight, (int, float)):
            return False, f"Weight for {code} must be a number"
        
        if weight < 0:
            return False, f"Weight for {code} cannot be negative"
        
        if weight > 1:
            return False, f"Weight for {code} cannot exceed 100%"
    
    # Check total weight
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 0.01:  # Allow 1% tolerance
        return False, f"Total weight {total_weight:.2%} should be 100%"
    
    return True, ""


def validate_signal(signal: Dict) -> tuple[bool, List[str]]:
    """
    Validate trading signal
    
    Args:
        signal: Signal dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    required_fields = [
        'code', 'signal_type', 'momentum_score', 
        'return_60d', 'return_120d'
    ]
    
    for field in required_fields:
        if field not in signal:
            errors.append(f"Missing required field: {field}")
    
    # Validate ETF code
    if 'code' in signal and not validate_etf_code(signal['code']):
        errors.append(f"Invalid ETF code: {signal.get('code')}")
    
    # Validate signal type
    valid_signal_types = ['BUY', 'SELL', 'HOLD', 'REBALANCE']
    if 'signal_type' in signal and signal['signal_type'] not in valid_signal_types:
        errors.append(f"Invalid signal type: {signal['signal_type']}")
    
    # Validate scores and returns
    numeric_fields = ['momentum_score', 'return_60d', 'return_120d']
    for field in numeric_fields:
        if field in signal:
            try:
                value = float(signal[field])
                if field.startswith('return') and abs(value) > 10:
                    errors.append(f"{field} seems unrealistic: {value}")
            except (ValueError, TypeError):
                errors.append(f"Invalid numeric value for {field}")
    
    return len(errors) == 0, errors


def validate_user_input(input_data: Dict, input_type: str) -> tuple[bool, List[str]]:
    """
    Generic user input validation
    
    Args:
        input_data: Input data dictionary
        input_type: Type of input ('order', 'parameter', 'signal', etc.)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    if input_type == 'order':
        return validate_orders([input_data])
    elif input_type == 'parameter':
        return validate_parameters(input_data)
    elif input_type == 'signal':
        return validate_signal(input_data)
    else:
        return False, [f"Unknown input type: {input_type}"]