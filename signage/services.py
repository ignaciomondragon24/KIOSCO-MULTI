import re
from decimal import Decimal


def format_currency(value):
    """Formatea un valor como moneda argentina: $1.234"""
    try:
        value = Decimal(str(value))
        integer_part = int(value)
        formatted = f"${integer_part:,}".replace(",", ".")
        return formatted
    except (TypeError, ValueError):
        return str(value)


def extract_weight(name):
    """Intenta extraer el gramaje/peso del nombre del producto."""
    patterns = [
        r'(\d+)\s*(?:grs?|gr)\b',
        r'(\d+)\s*g\b',
        r'(\d+)\s*(?:ml|cc)\b',
        r'(\d+(?:[.,]\d+)?)\s*(?:kg|lt|l)\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            return match.group(0).strip().upper()
    return ''


def auto_fill_product_data(product, sign_type, promo=None):
    """Auto-completa los datos de un cartel a partir de un producto."""
    data = {
        'nombre_producto': product.name.upper()
    }

    if sign_type == 'simple':
        data['precio_unitario'] = format_currency(product.sale_price)
        data['gramaje'] = extract_weight(product.name)

    elif sign_type == 'promo':
        data['precio_unitario'] = format_currency(product.sale_price)
        # If promo not passed, try to fetch (fallback for single-product usage)
        if promo is None:
            try:
                from promotions.models import Promotion
                promo = Promotion.objects.filter(
                    products=product,
                    status='active',
                    promo_type__in=['nxm', 'quantity_discount']
                ).first()
            except Exception:
                pass

        if promo:
            data['cantidad_promo'] = str(promo.quantity_required)
            charged_price = product.sale_price * promo.quantity_charged
            data['precio_promo'] = format_currency(charged_price)
            data['etiqueta_promo'] = 'PROMO!!'
        else:
            data['cantidad_promo'] = '2'
            data['precio_promo'] = ''
            data['etiqueta_promo'] = 'PROMO!!'

    elif sign_type == 'bulk':
        data['precio_total'] = format_currency(product.sale_price)
        if product.units_per_package and product.units_per_package > 1:
            data['tipo_empaque'] = 'CAJA'
            data['contenido_empaque'] = f'X {product.units_per_package}U.'
        elif product.is_bulk and product.bulk_unit in ('kg', 'g'):
            data['tipo_empaque'] = 'BOLSA'
            data['contenido_empaque'] = f'X 1{product.bulk_unit.upper()}'
        else:
            data['tipo_empaque'] = 'CAJA'
            data['contenido_empaque'] = f'X {product.units_per_package}U.'

    elif sign_type == 'weight':
        if product.is_bulk:
            kg_price = product.sale_price
            data['precio_1kg'] = format_currency(kg_price)
            data['precio_250g'] = format_currency(kg_price / 4)
            data['precio_100g'] = format_currency(kg_price / 10)
        else:
            data['precio_1kg'] = format_currency(product.sale_price)
            data['precio_250g'] = format_currency(product.sale_price * Decimal('0.25'))
            data['precio_100g'] = format_currency(product.sale_price * Decimal('0.1'))

    return data


PAPER_SIZES = {
    'A4': {'width': 210, 'height': 297},
    'A3': {'width': 297, 'height': 420},
    'letter': {'width': 216, 'height': 279},
}


def calculate_nesting(sign_width_mm, sign_height_mm, paper_size='A4', margin_mm=5, gap_mm=2):
    """Calcula el acomodo óptimo de carteles en una hoja."""
    paper = PAPER_SIZES.get(paper_size, PAPER_SIZES['A4'])

    usable_w = paper['width'] - 2 * margin_mm
    usable_h = paper['height'] - 2 * margin_mm

    # Orientación normal
    cols_n = max(1, int((usable_w + gap_mm) / (sign_width_mm + gap_mm)))
    rows_n = max(1, int((usable_h + gap_mm) / (sign_height_mm + gap_mm)))
    total_n = cols_n * rows_n

    # Orientación rotada
    cols_r = max(1, int((usable_w + gap_mm) / (sign_height_mm + gap_mm)))
    rows_r = max(1, int((usable_h + gap_mm) / (sign_width_mm + gap_mm)))
    total_r = cols_r * rows_r

    if total_r > total_n:
        return {
            'cols': cols_r, 'rows': rows_r,
            'total_per_page': total_r, 'rotated': True,
            'sign_width': sign_height_mm, 'sign_height': sign_width_mm,
            'margin': margin_mm, 'gap': gap_mm, 'paper': paper,
        }
    return {
        'cols': cols_n, 'rows': rows_n,
        'total_per_page': total_n, 'rotated': False,
        'sign_width': sign_width_mm, 'sign_height': sign_height_mm,
        'margin': margin_mm, 'gap': gap_mm, 'paper': paper,
    }
