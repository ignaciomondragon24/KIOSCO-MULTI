import json

from django.db import models
from django.conf import settings


# ─── Diseños pre-armados B&W con logo para impresión ───

LOGO_URL = '/static/img/logo.png'

DEFAULT_LAYOUTS = {
    'simple_40x40': {
        'name': 'Simple Clásico',
        'sign_type': 'simple',
        'width_mm': 40, 'height_mm': 40,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header bar negro con logo
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 40, 'height': 5,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 0.5, 'y': 0.3, 'width': 12, 'height': 4.4, 'zIndex': 20},
                # Nombre del producto — area generosa para nombres largos
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 1.5, 'y': 6, 'width': 37, 'height': 13,
                 'fontFamily': 'Arial', 'fontSize': 10, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 5, 'zIndex': 10},
                # Gramaje
                {'id': 'gramaje', 'type': 'variable', 'variable': 'gramaje',
                 'x': 8, 'y': 19, 'width': 24, 'height': 4,
                 'fontFamily': 'Arial', 'fontSize': 6, 'fontWeight': 'normal',
                 'fontStyle': 'italic', 'color': '#888888', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 4, 'zIndex': 10},
                # Línea separadora
                {'id': 'sep', 'type': 'line', 'x': 3, 'y': 23.5, 'width': 34, 'height': 0.3,
                 'lineColor': '#000000', 'lineWidth': 0.4, 'lineStyle': 'solid', 'zIndex': 5},
                # Precio — grande y centrado
                {'id': 'precio', 'type': 'variable', 'variable': 'precio_unitario',
                 'x': 1.5, 'y': 24, 'width': 37, 'height': 15,
                 'fontFamily': 'Arial', 'fontSize': 22, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 12, 'zIndex': 10},
            ]
        }
    },
    'simple_50x30': {
        'name': 'Simple Compacto',
        'sign_type': 'simple',
        'width_mm': 50, 'height_mm': 30,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header bar
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 50, 'height': 4.5,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 0.5, 'y': 0.2, 'width': 12, 'height': 4, 'zIndex': 20},
                # Nombre — generoso
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 2, 'y': 5, 'width': 46, 'height': 10,
                 'fontFamily': 'Arial', 'fontSize': 9, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 5, 'zIndex': 10},
                # Gramaje inline
                {'id': 'gramaje', 'type': 'variable', 'variable': 'gramaje',
                 'x': 14, 'y': 14.5, 'width': 22, 'height': 3,
                 'fontFamily': 'Arial', 'fontSize': 5, 'fontWeight': 'normal',
                 'fontStyle': 'italic', 'color': '#888888', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 4, 'zIndex': 10},
                # Línea
                {'id': 'sep', 'type': 'line', 'x': 3, 'y': 18, 'width': 44, 'height': 0.3,
                 'lineColor': '#000000', 'lineWidth': 0.4, 'lineStyle': 'solid', 'zIndex': 5},
                # Precio
                {'id': 'precio', 'type': 'variable', 'variable': 'precio_unitario',
                 'x': 2, 'y': 18.5, 'width': 46, 'height': 10.5,
                 'fontFamily': 'Arial', 'fontSize': 18, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 10, 'zIndex': 10},
            ]
        }
    },
    'promo_70x50': {
        'name': 'Promo Clásico',
        'sign_type': 'promo',
        'width_mm': 70, 'height_mm': 50,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro con logo + etiqueta promo
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 70, 'height': 7,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 1, 'y': 0.5, 'width': 14, 'height': 6, 'zIndex': 20},
                {'id': 'etiqueta', 'type': 'variable', 'variable': 'etiqueta_promo',
                 'x': 16, 'y': 0.5, 'width': 52, 'height': 6,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 7, 'zIndex': 10},
                # Nombre producto — area grande
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 3, 'y': 8.5, 'width': 64, 'height': 12,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 6, 'zIndex': 10},
                # Precio tachado (anterior)
                {'id': 'precio_ant', 'type': 'variable', 'variable': 'precio_unitario',
                 'x': 3, 'y': 21, 'width': 64, 'height': 6,
                 'fontFamily': 'Arial', 'fontSize': 8, 'fontWeight': 'normal',
                 'textDecoration': 'line-through',
                 'color': '#999999', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 5, 'zIndex': 10},
                # Box de promo
                {'id': 'promo_box', 'type': 'shape', 'x': 3, 'y': 28, 'width': 64, 'height': 19,
                 'backgroundColor': '#f0f0f0', 'borderColor': '#000000',
                 'borderWidth': 0.4, 'borderRadius': 2, 'zIndex': 3},
                {'id': 'cantidad', 'type': 'variable', 'variable': 'cantidad_promo',
                 'x': 5, 'y': 29, 'width': 16, 'height': 16,
                 'fontFamily': 'Arial', 'fontSize': 22, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'right', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 12, 'zIndex': 10},
                {'id': 'x_label', 'type': 'text', 'content': 'X',
                 'x': 22, 'y': 31, 'width': 8, 'height': 12,
                 'fontFamily': 'Arial', 'fontSize': 12, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'precio_promo', 'type': 'variable', 'variable': 'precio_promo',
                 'x': 30, 'y': 29, 'width': 35, 'height': 16,
                 'fontFamily': 'Arial', 'fontSize': 22, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 12, 'zIndex': 10},
            ]
        }
    },
    'promo_100x70': {
        'name': 'Promo Grande',
        'sign_type': 'promo',
        'width_mm': 100, 'height_mm': 70,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 100, 'height': 10,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 2, 'y': 1, 'width': 20, 'height': 8, 'zIndex': 20},
                {'id': 'etiqueta', 'type': 'variable', 'variable': 'etiqueta_promo',
                 'x': 24, 'y': 1, 'width': 72, 'height': 8,
                 'fontFamily': 'Arial', 'fontSize': 16, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 10, 'zIndex': 10},
                # Nombre — area grande
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 5, 'y': 12, 'width': 90, 'height': 16,
                 'fontFamily': 'Arial', 'fontSize': 15, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 8, 'zIndex': 10},
                # Precio tachado
                {'id': 'precio_ant', 'type': 'variable', 'variable': 'precio_unitario',
                 'x': 10, 'y': 29, 'width': 80, 'height': 7,
                 'fontFamily': 'Arial', 'fontSize': 10, 'fontWeight': 'normal',
                 'textDecoration': 'line-through',
                 'color': '#999999', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 7, 'zIndex': 10},
                # Box promo grande
                {'id': 'promo_box', 'type': 'shape', 'x': 5, 'y': 38, 'width': 90, 'height': 28,
                 'backgroundColor': '#f0f0f0', 'borderColor': '#000000',
                 'borderWidth': 0.4, 'borderRadius': 3, 'zIndex': 3},
                {'id': 'cantidad', 'type': 'variable', 'variable': 'cantidad_promo',
                 'x': 8, 'y': 40, 'width': 24, 'height': 24,
                 'fontFamily': 'Arial', 'fontSize': 34, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'right', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 16, 'zIndex': 10},
                {'id': 'x_label', 'type': 'text', 'content': 'X',
                 'x': 34, 'y': 44, 'width': 12, 'height': 16,
                 'fontFamily': 'Arial', 'fontSize': 16, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'precio_promo', 'type': 'variable', 'variable': 'precio_promo',
                 'x': 46, 'y': 40, 'width': 46, 'height': 24,
                 'fontFamily': 'Arial', 'fontSize': 34, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 16, 'zIndex': 10},
            ]
        }
    },
    'bulk_100x70': {
        'name': 'Bulto Clásico',
        'sign_type': 'bulk',
        'width_mm': 100, 'height_mm': 70,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 100, 'height': 10,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 2, 'y': 1, 'width': 20, 'height': 8, 'zIndex': 20},
                # Nombre — area generosa
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 4, 'y': 12, 'width': 92, 'height': 16,
                 'fontFamily': 'Arial', 'fontSize': 14, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 7, 'zIndex': 10},
                # Línea separadora
                {'id': 'sep', 'type': 'line', 'x': 8, 'y': 29, 'width': 84, 'height': 0.4,
                 'lineColor': '#000000', 'lineWidth': 0.4, 'lineStyle': 'solid', 'zIndex': 5},
                # Precio grande
                {'id': 'precio', 'type': 'variable', 'variable': 'precio_total',
                 'x': 5, 'y': 30, 'width': 90, 'height': 22,
                 'fontFamily': 'Arial', 'fontSize': 32, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 14, 'zIndex': 10},
                # Footer bar con empaque info
                {'id': 'footer', 'type': 'shape', 'x': 10, 'y': 54, 'width': 80, 'height': 13,
                 'backgroundColor': '#f0f0f0', 'borderColor': '#000000',
                 'borderWidth': 0.3, 'borderRadius': 2, 'zIndex': 5},
                {'id': 'empaque', 'type': 'variable', 'variable': 'tipo_empaque',
                 'x': 12, 'y': 55, 'width': 34, 'height': 11,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'right', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 7, 'zIndex': 10},
                {'id': 'contenido', 'type': 'variable', 'variable': 'contenido_empaque',
                 'x': 48, 'y': 55, 'width': 40, 'height': 11,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'left', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 7, 'zIndex': 10},
            ]
        }
    },
    'bulk_140x100': {
        'name': 'Bulto Grande',
        'sign_type': 'bulk',
        'width_mm': 140, 'height_mm': 100,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 140, 'height': 14,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 3, 'y': 2, 'width': 26, 'height': 10, 'zIndex': 20},
                # Nombre — extra grande
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 6, 'y': 17, 'width': 128, 'height': 22,
                 'fontFamily': 'Arial', 'fontSize': 20, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 10, 'zIndex': 10},
                # Línea
                {'id': 'sep', 'type': 'line', 'x': 12, 'y': 41, 'width': 116, 'height': 0.4,
                 'lineColor': '#000000', 'lineWidth': 0.4, 'lineStyle': 'solid', 'zIndex': 5},
                # Precio enorme
                {'id': 'precio', 'type': 'variable', 'variable': 'precio_total',
                 'x': 10, 'y': 43, 'width': 120, 'height': 32,
                 'fontFamily': 'Arial', 'fontSize': 46, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 20, 'zIndex': 10},
                # Footer empaque
                {'id': 'footer', 'type': 'shape', 'x': 20, 'y': 79, 'width': 100, 'height': 17,
                 'backgroundColor': '#f0f0f0', 'borderColor': '#000000',
                 'borderWidth': 0.3, 'borderRadius': 3, 'zIndex': 5},
                {'id': 'empaque', 'type': 'variable', 'variable': 'tipo_empaque',
                 'x': 24, 'y': 81, 'width': 42, 'height': 13,
                 'fontFamily': 'Arial', 'fontSize': 14, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'right', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 9, 'zIndex': 10},
                {'id': 'contenido', 'type': 'variable', 'variable': 'contenido_empaque',
                 'x': 70, 'y': 81, 'width': 48, 'height': 13,
                 'fontFamily': 'Arial', 'fontSize': 14, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'left', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 9, 'zIndex': 10},
            ]
        }
    },
    'weight_100x70': {
        'name': 'Peso Clásico',
        'sign_type': 'weight',
        'width_mm': 100, 'height_mm': 70,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 100, 'height': 10,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 2, 'y': 1, 'width': 20, 'height': 8, 'zIndex': 20},
                # Nombre generoso
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 4, 'y': 12, 'width': 92, 'height': 14,
                 'fontFamily': 'Arial', 'fontSize': 13, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 6, 'zIndex': 10},
                # Línea separadora
                {'id': 'sep', 'type': 'line', 'x': 5, 'y': 27, 'width': 90, 'height': 0.4,
                 'lineColor': '#000000', 'lineWidth': 0.3, 'lineStyle': 'solid', 'zIndex': 5},
                # 3 columnas: 100g, 250g, 1kg
                {'id': 'lbl100', 'type': 'text', 'content': '100 GR',
                 'x': 2, 'y': 28, 'width': 30, 'height': 6,
                 'fontFamily': 'Arial', 'fontSize': 7, 'fontWeight': 'bold',
                 'color': '#666666', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'p100', 'type': 'variable', 'variable': 'precio_100g',
                 'x': 2, 'y': 34, 'width': 30, 'height': 14,
                 'fontFamily': 'Arial', 'fontSize': 16, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 8, 'zIndex': 10},
                {'id': 'lbl250', 'type': 'text', 'content': '¼ Kg',
                 'x': 35, 'y': 28, 'width': 30, 'height': 6,
                 'fontFamily': 'Arial', 'fontSize': 7, 'fontWeight': 'bold',
                 'color': '#666666', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'p250', 'type': 'variable', 'variable': 'precio_250g',
                 'x': 35, 'y': 34, 'width': 30, 'height': 14,
                 'fontFamily': 'Arial', 'fontSize': 16, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 8, 'zIndex': 10},
                # Columna Kg destacada
                {'id': 'kgBox', 'type': 'shape', 'x': 66, 'y': 27, 'width': 32, 'height': 22,
                 'backgroundColor': '#000000', 'borderColor': '#000000',
                 'borderWidth': 0.3, 'borderRadius': 2, 'zIndex': 3},
                {'id': 'lblKg', 'type': 'text', 'content': 'Kg',
                 'x': 68, 'y': 28, 'width': 28, 'height': 6,
                 'fontFamily': 'Arial', 'fontSize': 8, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'pKg', 'type': 'variable', 'variable': 'precio_1kg',
                 'x': 68, 'y': 34, 'width': 28, 'height': 14,
                 'fontFamily': 'Arial', 'fontSize': 20, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 10, 'zIndex': 10},
                # Pie
                {'id': 'foot', 'type': 'text', 'content': 'VENTA AL PESO',
                 'x': 20, 'y': 52, 'width': 60, 'height': 14,
                 'fontFamily': 'Arial', 'fontSize': 8, 'fontWeight': 'bold',
                 'color': '#999999', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
            ]
        }
    },
    'weight_140x100': {
        'name': 'Peso Grande',
        'sign_type': 'weight',
        'width_mm': 140, 'height_mm': 100,
        'layout': {
            'background_color': '#FFFFFF',
            'border_color': '#000000',
            'border_width': 0.5,
            'elements': [
                # Header negro
                {'id': 'header', 'type': 'shape', 'x': 0, 'y': 0, 'width': 140, 'height': 14,
                 'backgroundColor': '#000000', 'zIndex': 2},
                {'id': 'logo', 'type': 'image', 'src': LOGO_URL,
                 'x': 3, 'y': 2, 'width': 26, 'height': 10, 'zIndex': 20},
                # Nombre extra grande
                {'id': 'nombre', 'type': 'variable', 'variable': 'nombre_producto',
                 'x': 6, 'y': 17, 'width': 128, 'height': 20,
                 'fontFamily': 'Arial', 'fontSize': 18, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 9, 'zIndex': 10},
                # Línea
                {'id': 'sep', 'type': 'line', 'x': 8, 'y': 39, 'width': 124, 'height': 0.4,
                 'lineColor': '#000000', 'lineWidth': 0.4, 'lineStyle': 'solid', 'zIndex': 5},
                # 3 columnas
                {'id': 'lbl100', 'type': 'text', 'content': '100 GR',
                 'x': 3, 'y': 41, 'width': 42, 'height': 10,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#666666', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'p100', 'type': 'variable', 'variable': 'precio_100g',
                 'x': 3, 'y': 51, 'width': 42, 'height': 20,
                 'fontFamily': 'Arial', 'fontSize': 22, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 12, 'zIndex': 10},
                {'id': 'lbl250', 'type': 'text', 'content': '¼ Kg',
                 'x': 49, 'y': 41, 'width': 42, 'height': 10,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#666666', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'p250', 'type': 'variable', 'variable': 'precio_250g',
                 'x': 49, 'y': 51, 'width': 42, 'height': 20,
                 'fontFamily': 'Arial', 'fontSize': 22, 'fontWeight': 'bold',
                 'color': '#000000', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 12, 'zIndex': 10},
                # Columna Kg destacada negra
                {'id': 'kgBox', 'type': 'shape', 'x': 94, 'y': 39, 'width': 43, 'height': 34,
                 'backgroundColor': '#000000', 'borderColor': '#000000',
                 'borderWidth': 0.3, 'borderRadius': 3, 'zIndex': 3},
                {'id': 'lblKg', 'type': 'text', 'content': 'Kg',
                 'x': 96, 'y': 41, 'width': 39, 'height': 10,
                 'fontFamily': 'Arial', 'fontSize': 12, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
                {'id': 'pKg', 'type': 'variable', 'variable': 'precio_1kg',
                 'x': 96, 'y': 51, 'width': 39, 'height': 20,
                 'fontFamily': 'Arial', 'fontSize': 28, 'fontWeight': 'bold',
                 'color': '#FFFFFF', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': True, 'minFontSize': 14, 'zIndex': 10},
                # Pie
                {'id': 'foot', 'type': 'text', 'content': 'VENTA AL PESO',
                 'x': 30, 'y': 78, 'width': 80, 'height': 18,
                 'fontFamily': 'Arial', 'fontSize': 11, 'fontWeight': 'bold',
                 'color': '#999999', 'backgroundColor': 'transparent',
                 'textAlign': 'center', 'verticalAlign': 'middle',
                 'autoScale': False, 'zIndex': 10},
            ]
        }
    },
}


def ensure_default_templates():
    """Crea las plantillas predeterminadas si no existen."""
    created = 0
    for key, data in DEFAULT_LAYOUTS.items():
        exists = SignTemplate.objects.filter(
            sign_type=data['sign_type'],
            width_mm=data['width_mm'],
            height_mm=data['height_mm'],
            is_default=True,
        ).exists()
        if not exists:
            SignTemplate.objects.create(
                name=data['name'],
                sign_type=data['sign_type'],
                width_mm=data['width_mm'],
                height_mm=data['height_mm'],
                layout_json=json.dumps(data['layout']),
                is_default=True,
                is_active=True,
            )
            created += 1
    return created


class SignTemplate(models.Model):
    """Plantilla (molde) de cartel para inyectar datos de productos."""

    SIGN_TYPES = [
        ('simple', 'Cartel Simple (Precio Unitario)'),
        ('promo', 'Cartel Promocional (Llevá X por Y)'),
        ('bulk', 'Cartel de Bulto Cerrado (Caja/Bolsa)'),
        ('weight', 'Cartel de Venta al Peso'),
    ]

    PRESET_SIZES = {
        'simple': [
            {'label': '4 × 4 cm', 'width': 40, 'height': 40},
            {'label': '5 × 3 cm', 'width': 50, 'height': 30},
        ],
        'promo': [
            {'label': '7 × 5 cm', 'width': 70, 'height': 50},
            {'label': '10 × 7 cm', 'width': 100, 'height': 70},
        ],
        'bulk': [
            {'label': '10 × 7 cm', 'width': 100, 'height': 70},
            {'label': '14 × 10 cm (A6)', 'width': 140, 'height': 100},
        ],
        'weight': [
            {'label': '10 × 7 cm (apaisado)', 'width': 100, 'height': 70},
            {'label': '14 × 10 cm', 'width': 140, 'height': 100},
        ],
    }

    name = models.CharField('Nombre', max_length=200)
    sign_type = models.CharField('Tipo de Cartel', max_length=20, choices=SIGN_TYPES)
    width_mm = models.PositiveIntegerField('Ancho (mm)')
    height_mm = models.PositiveIntegerField('Alto (mm)')
    layout_json = models.TextField('Diseño (JSON)', default='{}', blank=True)

    @property
    def layout(self):
        try:
            return json.loads(self.layout_json) if self.layout_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @layout.setter
    def layout(self, value):
        self.layout_json = json.dumps(value) if value else '{}'

    is_active = models.BooleanField('Activo', default=True)
    is_default = models.BooleanField('Predeterminado', default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plantilla de Cartel'
        verbose_name_plural = 'Plantillas de Carteles'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.get_sign_type_display()}) - {self.width_mm}×{self.height_mm}mm"

    @property
    def size_label(self):
        w_cm = self.width_mm / 10
        h_cm = self.height_mm / 10
        return f"{w_cm:.0f} × {h_cm:.0f} cm"

    @classmethod
    def get_type_variables(cls, sign_type):
        """Variables disponibles para cada tipo de cartel."""
        VARIABLES = {
            'simple': [
                {'key': 'nombre_producto', 'label': 'Nombre del Producto', 'sample': 'SALADIX'},
                {'key': 'gramaje', 'label': 'Gramaje', 'sample': '100g'},
                {'key': 'precio_unitario', 'label': 'Precio Unitario', 'sample': '$790'},
            ],
            'promo': [
                {'key': 'nombre_producto', 'label': 'Nombre del Producto', 'sample': 'TURRON MISKY'},
                {'key': 'precio_unitario', 'label': 'Precio Unitario', 'sample': '$180'},
                {'key': 'cantidad_promo', 'label': 'Cantidad Promo', 'sample': '3'},
                {'key': 'precio_promo', 'label': 'Precio Promo', 'sample': '$500'},
                {'key': 'etiqueta_promo', 'label': 'Etiqueta (PROMO!!)', 'sample': 'PROMO!!'},
            ],
            'bulk': [
                {'key': 'nombre_producto', 'label': 'Nombre del Producto', 'sample': 'FEELING'},
                {'key': 'precio_total', 'label': 'Precio Total', 'sample': '$11.500'},
                {'key': 'tipo_empaque', 'label': 'Tipo de Empaque', 'sample': 'CAJA'},
                {'key': 'contenido_empaque', 'label': 'Contenido', 'sample': 'X 30U.'},
            ],
            'weight': [
                {'key': 'nombre_producto', 'label': 'Nombre del Producto', 'sample': 'ALMENDRAS PELADAS'},
                {'key': 'precio_100g', 'label': 'Precio 100g', 'sample': '$3.200'},
                {'key': 'precio_250g', 'label': 'Precio ¼ Kg', 'sample': '$7.350'},
                {'key': 'precio_1kg', 'label': 'Precio 1 Kg', 'sample': '$29.400'},
            ],
        }
        return VARIABLES.get(sign_type, [])


class SignBatch(models.Model):
    """Lote de carteles generados."""

    PAPER_SIZES = [
        ('A4', 'A4 (210 × 297 mm)'),
        ('A3', 'A3 (297 × 420 mm)'),
        ('letter', 'Carta (216 × 279 mm)'),
    ]

    name = models.CharField('Nombre', max_length=200, blank=True)
    template = models.ForeignKey(
        SignTemplate, on_delete=models.CASCADE,
        related_name='batches', verbose_name='Plantilla'
    )
    paper_size = models.CharField(
        'Tamaño de Papel', max_length=10,
        choices=PAPER_SIZES, default='A4'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Creado por'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lote de Carteles'
        verbose_name_plural = 'Lotes de Carteles'
        ordering = ['-created_at']

    def __str__(self):
        return f"Lote #{self.pk} - {self.template.name} ({self.created_at:%d/%m/%Y})"

    @property
    def total_signs(self):
        return sum(item.copies for item in self.items.all())


class SignItem(models.Model):
    """Item individual en un lote de carteles."""

    batch = models.ForeignKey(
        SignBatch, on_delete=models.CASCADE,
        related_name='items', verbose_name='Lote'
    )
    product = models.ForeignKey(
        'stocks.Product', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Producto'
    )
    data_json = models.TextField('Datos (JSON)', default='{}', blank=True)

    @property
    def data(self):
        try:
            return json.loads(self.data_json) if self.data_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value) if value else '{}'
    copies = models.PositiveIntegerField('Copias', default=1)
    order = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Item de Cartel'
        verbose_name_plural = 'Items de Carteles'
        ordering = ['order']

    def __str__(self):
        name = self.data.get('nombre_producto', f'Item #{self.pk}')
        return f"{name} ×{self.copies}"
