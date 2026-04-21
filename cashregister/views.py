"""
Cash Register Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q
from django.db import models
from django.utils import timezone
from decimal import Decimal

from .models import CashRegister, CashShift, CashMovement, PaymentMethod
from .forms import OpenShiftForm, CloseShiftForm, MovementForm
from decorators.decorators import group_required


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def dashboard(request):
    """Cash register dashboard."""
    registers = CashRegister.objects.filter(is_active=True)
    open_shifts = CashShift.objects.filter(status='open').select_related('cash_register', 'cashier')
    user_shift = CashShift.objects.filter(cashier=request.user, status='open').first()
    
    context = {
        'registers': registers,
        'open_shifts': open_shifts,
        'user_shift': user_shift,
    }
    
    return render(request, 'cashregister/dashboard.html', context)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def open_shift(request):
    """Open a new cash shift."""
    # Check if user already has an open shift
    existing_shift = CashShift.objects.filter(cashier=request.user, status='open').first()
    if existing_shift:
        messages.warning(request, 'Ya tienes un turno abierto.')
        return redirect('cashregister:shift_detail', pk=existing_shift.pk)
    
    if request.method == 'POST':
        form = OpenShiftForm(request.POST)
        if form.is_valid():
            cash_register = form.cleaned_data['cash_register']
            
            # Check if register is available
            if not cash_register.is_available:
                messages.error(request, f'La caja {cash_register.code} ya tiene un turno abierto.')
                return redirect('cashregister:dashboard')
            
            shift = CashShift.objects.create(
                cash_register=cash_register,
                cashier=request.user,
                initial_amount=form.cleaned_data['initial_amount']
            )
            
            messages.success(request, f'Turno abierto en {cash_register.code}.')
            return redirect('cashregister:shift_detail', pk=shift.pk)
    else:
        form = OpenShiftForm()
    
    return render(request, 'cashregister/open_shift.html', {'form': form})


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def close_shift(request, pk):
    """Close a cash shift with bill counting (Cierre Z)."""
    from .models import BillCount, ShiftPaymentSummary
    
    shift = get_object_or_404(CashShift, pk=pk)
    
    # Verify permissions
    if shift.cashier != request.user and not request.user.is_admin:
        messages.error(request, 'No puedes cerrar un turno de otro cajero.')
        return redirect('cashregister:dashboard')
    
    if shift.status == 'closed':
        messages.warning(request, 'Este turno ya está cerrado.')
        return redirect('cashregister:shift_detail', pk=pk)
    
    # Calculate expected amount (only cash)
    expected = shift.calculate_expected()
    
    # Get totals by payment method
    payment_methods = shift.get_totals_by_payment_method()
    cash_total = shift.get_cash_total()
    non_cash_total = shift.get_non_cash_total()
    
    # Get cash expenses
    cash_expense = shift.movements.filter(
        movement_type='expense',
        payment_method__is_cash=True
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Total sales (all methods)
    total_sales = cash_total + non_cash_total
    
    if request.method == 'POST':
        form = CloseShiftForm(request.POST)
        if form.is_valid():
            actual_amount = form.cleaned_data['actual_amount']
            notes = form.cleaned_data['notes']
            
            # Save bill counts
            bill_denominations = [
                ('bill_20000', 20000),
                ('bill_10000', 10000),
                ('bill_5000', 5000),
                ('bill_2000', 2000),
                ('bill_1000', 1000),
                ('bill_500', 500),
                ('bill_200', 200),
                ('bill_100', 100),
            ]
            
            for field_name, denomination in bill_denominations:
                quantity = int(request.POST.get(field_name, 0) or 0)
                if quantity > 0:
                    BillCount.objects.create(
                        cash_shift=shift,
                        denomination=denomination,
                        quantity=quantity,
                        count_type='closing'
                    )
            
            # Save coins as denomination 1
            coins = int(request.POST.get('coins', 0) or 0)
            if coins > 0:
                BillCount.objects.create(
                    cash_shift=shift,
                    denomination=1,
                    quantity=coins,
                    count_type='closing'
                )
            
            # Save payment summaries
            for pm in payment_methods:
                if pm['total']:
                    method = PaymentMethod.objects.get(code=pm['payment_method__code'])
                    ShiftPaymentSummary.objects.create(
                        cash_shift=shift,
                        payment_method=method,
                        total_amount=pm['total'],
                        transaction_count=pm['count']
                    )
            
            # Close the shift
            shift.close(actual_amount, notes)
            
            messages.success(request, f'Cierre Z completado. Diferencia: ${shift.difference:,.2f}'.replace(',', '.'))
            return redirect('cashregister:shift_detail', pk=pk)
    else:
        form = CloseShiftForm(initial={'actual_amount': expected})
    
    # Format payment methods for template
    formatted_methods = []
    for pm in payment_methods:
        formatted_methods.append({
            'code': pm['payment_method__code'],
            'name': pm['payment_method__name'],
            'icon': pm['payment_method__icon'] or 'fas fa-money-bill',
            'color': pm['payment_method__color'] or '#6c757d',
            'is_cash': pm['payment_method__is_cash'],
            'total': pm['total'] or Decimal('0.00'),
            'count': pm['count'] or 0,
        })
    
    context = {
        'form': form,
        'shift': shift,
        'expected': expected,
        'payment_methods': formatted_methods,
        'cash_total': cash_total,
        'non_cash_total': non_cash_total,
        'cash_expense': cash_expense,
        'total_sales': total_sales,
    }
    
    return render(request, 'cashregister/close_shift.html', context)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def shift_detail(request, pk):
    """Shift detail view."""
    shift = get_object_or_404(CashShift, pk=pk)
    movements = shift.movements.select_related('payment_method', 'created_by').order_by('-created_at')
    
    # Get totals by payment method
    totals_by_method = shift.movements.values(
        'payment_method__name'
    ).annotate(
        income=Sum('amount', filter=Q(movement_type='income')),
        expense=Sum('amount', filter=Q(movement_type='expense'))
    )
    
    context = {
        'shift': shift,
        'movements': movements,
        'totals_by_method': totals_by_method,
    }
    
    return render(request, 'cashregister/shift_detail.html', context)


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def add_movement(request, shift_pk):
    """Add a manual movement to shift."""
    shift = get_object_or_404(CashShift, pk=shift_pk)
    
    if shift.status == 'closed':
        messages.error(request, 'No se pueden agregar movimientos a un turno cerrado.')
        return redirect('cashregister:shift_detail', pk=shift_pk)
    
    if request.method == 'POST':
        form = MovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.cash_shift = shift
            movement.created_by = request.user
            movement.save()
            
            messages.success(request, 'Movimiento registrado correctamente.')
            return redirect('cashregister:shift_detail', pk=shift_pk)
    else:
        form = MovementForm()
    
    return render(request, 'cashregister/movement_form.html', {
        'form': form,
        'shift': shift
    })


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def shift_list(request):
    """List all shifts."""
    shifts = CashShift.objects.select_related(
        'cash_register', 'cashier'
    ).order_by('-opened_at')
    
    # Filters
    register = request.GET.get('register', '')
    status = request.GET.get('status', '')
    cashier = request.GET.get('cashier', '')
    
    if register:
        shifts = shifts.filter(cash_register_id=register)
    if status:
        shifts = shifts.filter(status=status)
    if cashier:
        shifts = shifts.filter(cashier_id=cashier)
    
    registers = CashRegister.objects.filter(is_active=True)
    
    context = {
        'shifts': shifts[:50],
        'registers': registers,
        'selected_register': register,
        'selected_status': status,
    }
    
    return render(request, 'cashregister/shift_list.html', context)


@login_required
@group_required(['Admin'])
def register_list(request):
    """List all cash registers."""
    registers = CashRegister.objects.all()
    return render(request, 'cashregister/register_list.html', {'registers': registers})


@login_required
@group_required(['Admin'])
def movement_list(request):
    """List all cash movements."""
    movements = CashMovement.objects.select_related(
        'cash_shift__cash_register', 'cash_shift__cashier', 'payment_method', 'created_by'
    ).order_by('-created_at')
    
    # Filters
    shift_id = request.GET.get('shift', '')
    movement_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if shift_id:
        movements = movements.filter(cash_shift_id=shift_id)
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if date_from:
        movements = movements.filter(created_at__date__gte=date_from)
    if date_to:
        movements = movements.filter(created_at__date__lte=date_to)
    
    # Totals
    totals = movements.aggregate(
        total_income=Sum('amount', filter=Q(movement_type='income')),
        total_expense=Sum('amount', filter=Q(movement_type='expense'))
    )
    
    context = {
        'movements': movements[:100],
        'totals': totals,
        'selected_type': movement_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'cashregister/movement_list.html', context)


@login_required
@group_required(['Admin'])
def register_create(request):
    """Create a new cash register."""
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        
        if code and name:
            CashRegister.objects.create(
                code=code,
                name=name,
                location=location
            )
            messages.success(request, f'Caja {code} creada correctamente.')
            return redirect('cashregister:register_list')
        else:
            messages.error(request, 'Complete todos los campos requeridos.')
    
    return render(request, 'cashregister/register_form.html')


@login_required
@group_required(['Admin', 'Cajero Manager', 'Cashier'])
def shift_data_api(request, pk):
    """API endpoint for real-time shift data updates."""
    shift = get_object_or_404(CashShift, pk=pk)
    
    # Get totals by payment method
    from pos.models import POSTransaction
    
    # Sales from POS transactions
    pos_sales = POSTransaction.objects.filter(
        session__cash_shift=shift,
        status='completed'
    ).aggregate(
        total=Sum('total'),
        count=Count('id')
    )
    
    # Manual movements
    movements_income = shift.movements.filter(
        movement_type='income'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    movements_expense = shift.movements.filter(
        movement_type='expense'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Calculate expected
    expected = shift.calculate_expected()
    
    data = {
        'total_sales': float(pos_sales['total'] or 0),
        'transactions_count': pos_sales['count'] or 0,
        'initial_amount': float(shift.initial_amount),
        'expected': float(expected),
        'movements_income': float(movements_income),
        'movements_expense': float(movements_expense),
        'status': shift.status,
    }
    
    return JsonResponse(data)


@login_required
def shift_report_pdf(request, pk):
    """Generate PDF report for a shift."""
    shift = get_object_or_404(CashShift, pk=pk)

    from django.http import HttpResponse

    response = HttpResponse(content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="cierre_z_turno_{shift.pk}.txt"'

    def fmt_money(val):
        try:
            return f"${val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (TypeError, ValueError):
            return f"${val}"

    # Resumen por método de pago (desde summaries guardados o en tiempo real)
    method_lines = []
    if shift.status == 'closed' and shift.payment_summaries.exists():
        for summary in shift.payment_summaries.all():
            method_lines.append(
                f"  {summary.payment_method.name:<20} {summary.transaction_count:>4} tx   {fmt_money(summary.total_amount):>14}"
            )
    else:
        for pm in shift.get_totals_by_payment_method():
            name = pm.get('payment_method__name') or 'Sin especificar'
            total = pm.get('total') or Decimal('0.00')
            count = pm.get('count') or 0
            method_lines.append(f"  {name:<20} {count:>4} tx   {fmt_money(total):>14}")
    method_block = '\n'.join(method_lines) if method_lines else '  (sin ventas registradas)'

    cash_total = shift.get_cash_total()
    non_cash_total = shift.get_non_cash_total()
    cash_expense = shift.movements.filter(
        movement_type='expense',
        payment_method__is_cash=True
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_sales = cash_total + non_cash_total

    content = f"""
CIERRE Z - REPORTE DE TURNO
============================

Caja:      {shift.cash_register.code}
Cajero:    {shift.cashier.get_full_name() or shift.cashier.username}
Apertura:  {shift.opened_at.strftime('%d/%m/%Y %H:%M')}
Cierre:    {shift.closed_at.strftime('%d/%m/%Y %H:%M') if shift.closed_at else 'Abierto'}
Estado:    {shift.get_status_display()}

VENTAS POR MÉTODO DE PAGO
-------------------------
{method_block}

  {'─' * 52}
  {'TOTAL VENTAS':<20} {'':>7}   {fmt_money(total_sales):>14}

ARQUEO DE EFECTIVO
------------------
Fondo Inicial:         {fmt_money(shift.initial_amount):>14}
+ Ventas Efectivo:     {fmt_money(cash_total):>14}
- Egresos Efectivo:    {fmt_money(cash_expense):>14}
= Efectivo Esperado:   {fmt_money(shift.expected_amount or Decimal('0.00')):>14}
  Efectivo Contado:    {(fmt_money(shift.actual_amount) if shift.actual_amount is not None else 'N/A'):>14}
  Diferencia:          {(fmt_money(shift.difference) if shift.difference is not None else 'N/A'):>14}

Ventas Digitales:      {fmt_money(non_cash_total):>14}

NOTAS
-----
{shift.notes or 'Sin notas'}
"""

    response.write(content)
    return response
