"""Test cascade logic consistency."""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'superrecord.settings'
django.setup()
from decimal import Decimal

print('=== ESCENARIO: Recibir 2 bultos (12 displays/bulto, 24 unidades/display) ===')
units_per_display = 24
displays_per_bulk = 12
units_quantity = units_per_display * displays_per_bulk  # 288

qty_received = Decimal('2')
units_added = qty_received * Decimal(str(units_quantity))
print(f'Unidades base agregadas: {units_added}')
print(f'Bulk stock: +{qty_received} = {qty_received}')
display_added = units_added / Decimal(str(units_per_display))
print(f'Display stock: +{display_added} = {display_added}')
print(f'Unit stock: +{units_added} = {units_added}')
print(f'Product.current_stock: +{units_added} = {units_added}')

print()
print('=== ESCENARIO: Vender 48 unidades ===')
sell_qty = Decimal('48')
final_product = units_added - sell_qty
final_unit = units_added - sell_qty
final_display = display_added - sell_qty / Decimal(str(units_per_display))
final_bulk = qty_received - sell_qty / Decimal(str(units_quantity))
print(f'Product: {units_added} - {sell_qty} = {final_product}')
print(f'Unit: {units_added} - {sell_qty} = {final_unit}')
print(f'Display: {display_added} - {sell_qty/Decimal(str(units_per_display))} = {final_display}')
print(f'Bulk: {qty_received} - {sell_qty/Decimal(str(units_quantity)):.4f} = {final_bulk:.4f}')

print()
print('=== VALIDACION ===')
eq_from_unit = final_unit
eq_from_display = final_display * units_per_display
eq_from_bulk = final_bulk * units_quantity
print(f'Unidades desde Unit: {eq_from_unit}')
print(f'Unidades desde Display: {eq_from_display}')
print(f'Unidades desde Bulk: {eq_from_bulk}')
print(f'Product.current_stock: {final_product}')
all_ok = (eq_from_unit == eq_from_display == eq_from_bulk == final_product)
print(f'TODO CONSISTENTE: {all_ok}')

print()
print('=== ESCENARIO: Ajustar bulto de 1.833... a 2 ===')
adjusted_bulk = Decimal('2')
diff_bulk = adjusted_bulk - final_bulk
units_diff = diff_bulk * units_quantity
new_product = final_product + units_diff
new_unit = final_unit + units_diff
new_display = final_display + units_diff / Decimal(str(units_per_display))
print(f'Diff bultos: {diff_bulk:.4f} => diff unidades: {units_diff:.2f}')
print(f'Product: {new_product}')
print(f'Unit: {new_unit}')
print(f'Display: {new_display:.4f}')
print(f'Bulk: {adjusted_bulk}')
eq2 = new_unit == new_display * units_per_display == adjusted_bulk * units_quantity == new_product
print(f'TODO CONSISTENTE: {eq2}')
