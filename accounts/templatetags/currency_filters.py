"""
Custom template tags for currency formatting (Argentine Pesos)
"""
from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter(name='currency_ar')
def currency_ar(value):
    """
    Format a number as Argentine Peso currency.
    Example: 1234.56 -> $1.234
    """
    if value is None:
        return '$0'
    
    try:
        value = Decimal(str(value))
        # Format with thousand separator only (no decimals)
        formatted = '{:,.0f}'.format(value)
        # Replace comma with period for Argentine thousands separator
        formatted = formatted.replace(',', '.')
        return f'${formatted}'
    except (ValueError, TypeError, InvalidOperation):
        return '$0'


@register.filter(name='format_ar')
def format_ar(value):
    """
    Format a number with Argentine thousands separator (no decimals, no currency symbol).
    Example: 1234.56 -> 1.234
    """
    if value is None:
        return '0'
    
    try:
        value = Decimal(str(value))
        formatted = '{:,.0f}'.format(value)
        formatted = formatted.replace(',', '.')
        return formatted
    except (ValueError, TypeError, InvalidOperation):
        return '0'


@register.filter(name='format_quantity')
def format_quantity(value):
    """
    Format a quantity (remove trailing zeros).
    Example: 2.000 -> 2, 1.500 -> 1,5
    """
    if value is None:
        return '0'
    
    try:
        value = Decimal(str(value))
        # Remove trailing zeros
        formatted = '{:f}'.format(value.normalize())
        # Replace period with comma for Argentine format
        formatted = formatted.replace('.', ',')
        return formatted
    except (ValueError, TypeError, InvalidOperation):
        return '0'


@register.simple_tag
def currency_symbol():
    """Return the currency symbol."""
    return '$'


# Alias for currency_ar
@register.filter(name='currency')
def currency(value):
    """Alias for currency_ar."""
    return currency_ar(value)


@register.filter(name='divide')
def divide(value, arg):
    """
    Divide value by arg.
    Example: {{ 100|divide:4 }} -> 25
    """
    try:
        return Decimal(str(value)) / Decimal(str(arg))
    except (ValueError, TypeError, InvalidOperation, ZeroDivisionError):
        return 0


@register.filter(name='unlocalize')
def unlocalize_filter(value):
    """Return value as plain string, bypassing locale number formatting.
    Use for PKs/IDs inside form values, URL params and data-* attributes."""
    if value is None:
        return ''
    return str(value)


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiply value by arg.
    Example: {{ 10|multiply:5 }} -> 50
    """
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, InvalidOperation):
        return 0
