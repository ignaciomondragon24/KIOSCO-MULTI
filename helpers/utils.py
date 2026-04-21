"""
Utility functions for CHE GOLOSO
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import re


def format_currency_ar(value):
    """
    Format a value as Argentine peso.
    
    Args:
        value: Number to format
        
    Returns:
        Formatted string like '$1.234,56'
    """
    if value is None:
        return '$0'
    
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    
    # Format with thousands separator only (no decimals)
    formatted = '{:,.0f}'.format(value)
    # Replace for Argentine format (. for thousands)
    formatted = formatted.replace(',', '.')
    
    return f'${formatted}'


def parse_currency_ar(value_str):
    """
    Parse an Argentine currency string to Decimal.
    
    Args:
        value_str: String like '$1.234,56' or '1234.56'
        
    Returns:
        Decimal value
    """
    if not value_str:
        return Decimal('0.00')
    
    # Remove currency symbol and spaces
    cleaned = str(value_str).replace('$', '').replace(' ', '')
    
    # Handle Argentine format (. for thousands, , for decimals)
    if ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    
    try:
        return Decimal(cleaned)
    except:
        return Decimal('0.00')


def generate_ticket_number(cash_register_id, date=None):
    """
    Generate a unique ticket number.
    
    Format: CAJA-XX-YYYYMMDD-NNNN
    
    Args:
        cash_register_id: ID of the cash register
        date: Date for the ticket (defaults to today)
        
    Returns:
        Ticket number string
    """
    if date is None:
        date = datetime.now()
    
    from pos.models import POSTransaction
    
    date_str = date.strftime('%Y%m%d')
    prefix = f'CAJA-{cash_register_id:02d}-{date_str}'
    
    # Count existing tickets for today
    count = POSTransaction.objects.filter(
        ticket_number__startswith=prefix
    ).count() + 1
    
    return f'{prefix}-{count:04d}'


def validate_cuit(cuit):
    """
    Validate Argentine CUIT number.
    
    Args:
        cuit: CUIT string (with or without dashes)
        
    Returns:
        True if valid, False otherwise
    """
    # Remove dashes and spaces
    cuit = re.sub(r'[\s\-]', '', str(cuit))
    
    if len(cuit) != 11:
        return False
    
    if not cuit.isdigit():
        return False
    
    # Validate check digit
    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuit[i]) * base[i] for i in range(10))
    remainder = total % 11
    check_digit = 11 - remainder if remainder != 0 else 0
    
    if check_digit == 11:
        check_digit = 0
    
    return int(cuit[10]) == check_digit


def format_cuit(cuit):
    """
    Format CUIT with dashes: XX-XXXXXXXX-X
    
    Args:
        cuit: CUIT string without formatting
        
    Returns:
        Formatted CUIT string
    """
    cuit = re.sub(r'[\s\-]', '', str(cuit))
    
    if len(cuit) != 11:
        return cuit
    
    return f'{cuit[:2]}-{cuit[2:10]}-{cuit[10]}'


def validate_barcode(barcode):
    """
    Validate EAN-13 barcode.
    
    Args:
        barcode: Barcode string
        
    Returns:
        True if valid EAN-13, False otherwise
    """
    if not barcode or len(barcode) != 13:
        return False
    
    if not barcode.isdigit():
        return False
    
    # Calculate check digit
    total = 0
    for i, digit in enumerate(barcode[:12]):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    check_digit = (10 - (total % 10)) % 10
    
    return int(barcode[12]) == check_digit


def calculate_check_digit(barcode_without_check):
    """
    Calculate EAN-13 check digit.
    
    Args:
        barcode_without_check: First 12 digits of barcode
        
    Returns:
        Check digit (0-9)
    """
    if len(barcode_without_check) != 12:
        raise ValueError('Barcode must have 12 digits')
    
    total = 0
    for i, digit in enumerate(barcode_without_check):
        if i % 2 == 0:
            total += int(digit)
        else:
            total += int(digit) * 3
    
    return (10 - (total % 10)) % 10


def date_range(start_date, end_date):
    """
    Generate a range of dates.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Yields:
        Each date in the range
    """
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def get_period_dates(period='today'):
    """
    Get start and end dates for a period.
    
    Args:
        period: 'today', 'week', 'month', 'year', 'last_week', 'last_month'
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = datetime.now().date()
    
    if period == 'today':
        return today, today
    
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, today
    
    elif period == 'month':
        start = today.replace(day=1)
        return start, today
    
    elif period == 'year':
        start = today.replace(month=1, day=1)
        return start, today
    
    elif period == 'last_week':
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end
    
    elif period == 'last_month':
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
        return start, end
    
    return today, today


def truncate_string(text, max_length, suffix='...'):
    """
    Truncate a string to a maximum length.
    
    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated string
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
