"""
Expenses Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, Count
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta

from .models import ExpenseCategory, Expense, RecurringExpense
from .forms import ExpenseCategoryForm, ExpenseForm, RecurringExpenseForm
from decorators.decorators import group_required
from cashregister.models import CashShift, CashMovement, PaymentMethod


@login_required
@group_required(['Admin'])
def expense_list(request):
    """List all expenses."""
    expenses = Expense.objects.select_related('category', 'supplier', 'created_by').all()
    
    # Filters
    category = request.GET.get('category', '')
    if category:
        expenses = expenses.filter(category_id=category)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)
    
    search = request.GET.get('search', '')
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search) |
            Q(receipt_number__icontains=search)
        )
    
    # Calculate totals
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'expenses': expenses,
        'categories': ExpenseCategory.objects.filter(is_active=True),
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'total': total,
    }
    return render(request, 'expenses/expense_list.html', context)


@login_required
@group_required(['Admin'])
def expense_create(request):
    """Create a new expense."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            # Solo bloqueamos por turno cerrado si el gasto AFECTA el cajon —
            # un gasto operativo pagado por fuera (alquiler, sueldos) no necesita
            # turno abierto.
            if (form.cleaned_data.get('payment_method') == 'cash'
                    and form.cleaned_data.get('affects_cash_drawer')):
                active_shift = CashShift.objects.filter(status='open').first()
                if not active_shift:
                    messages.error(
                        request,
                        'Marcaste "sale del cajón" pero no hay turno abierto. '
                        'Abrí un turno o dejá el checkbox sin marcar.'
                    )
                    context = {'form': form, 'title': 'Nuevo Gasto'}
                    return render(request, 'expenses/expense_form.html', context)

            with transaction.atomic():
                expense = form.save(commit=False)
                expense.created_by = request.user
                expense.save()

                # CashMovement solo si el gasto sale del cajon del POS.
                if expense.payment_method == 'cash' and expense.affects_cash_drawer:
                    active_shift = CashShift.objects.filter(
                        status='open'
                    ).first()
                    cash_pm = PaymentMethod.objects.filter(is_cash=True).first()
                    if active_shift and cash_pm:
                        CashMovement.objects.create(
                            cash_shift=active_shift,
                            movement_type='expense',
                            amount=expense.amount,
                            payment_method=cash_pm,
                            description=f'Gasto: {expense.description}',
                            reference=f'EXP-{expense.id}',
                            created_by=request.user,
                        )

            messages.success(request, 'Gasto registrado exitosamente.')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(initial={'expense_date': timezone.now().date()})
    
    context = {'form': form, 'title': 'Nuevo Gasto'}
    return render(request, 'expenses/expense_form.html', context)


@login_required
@group_required(['Admin'])
def expense_edit(request, pk):
    """Edit an expense."""
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            ref = f'EXP-{expense.id}'
            existing_mov = CashMovement.objects.filter(reference=ref).first()
            wants_drawer = (form.cleaned_data.get('payment_method') == 'cash'
                            and form.cleaned_data.get('affects_cash_drawer'))
            if wants_drawer and not existing_mov:
                active_shift = CashShift.objects.filter(status='open').first()
                if not active_shift:
                    messages.error(
                        request,
                        'Marcaste "sale del cajón" pero no hay turno abierto. '
                        'Abrí un turno o dejá el checkbox sin marcar.'
                    )
                    context = {
                        'form': form, 'expense': expense,
                        'title': 'Editar Gasto'
                    }
                    return render(request, 'expenses/expense_form.html', context)

            with transaction.atomic():
                form.save()

                existing_mov = CashMovement.objects.filter(reference=ref).first()
                if expense.payment_method == 'cash' and expense.affects_cash_drawer:
                    active_shift = CashShift.objects.filter(status='open').first()
                    cash_pm = PaymentMethod.objects.filter(is_cash=True).first()
                    if existing_mov:
                        existing_mov.amount = expense.amount
                        existing_mov.description = f'Gasto: {expense.description}'
                        existing_mov.save()
                    elif active_shift and cash_pm:
                        CashMovement.objects.create(
                            cash_shift=active_shift,
                            movement_type='expense',
                            amount=expense.amount,
                            payment_method=cash_pm,
                            description=f'Gasto: {expense.description}',
                            reference=ref,
                            created_by=request.user,
                        )
                elif existing_mov:
                    # Ya no sale del cajon (cambio de metodo o destildo el flag):
                    # eliminamos el CashMovement para no afectar el cierre Z.
                    existing_mov.delete()

            messages.success(request, 'Gasto actualizado exitosamente.')
            return redirect('expenses:expense_list')
    else:
        form = ExpenseForm(instance=expense)
    
    context = {
        'form': form,
        'expense': expense,
        'title': 'Editar Gasto'
    }
    return render(request, 'expenses/expense_form.html', context)


@login_required
@group_required(['Admin'])
def expense_delete(request, pk):
    """Delete an expense."""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        with transaction.atomic():
            # Remove linked CashMovement if exists
            CashMovement.objects.filter(reference=f'EXP-{expense.id}').delete()
            expense.delete()
        messages.success(request, 'Gasto eliminado exitosamente.')
        return redirect('expenses:expense_list')
    
    context = {'expense': expense}
    return render(request, 'expenses/expense_confirm_delete.html', context)


@login_required
@group_required(['Admin'])
def category_list(request):
    """List expense categories."""
    categories = ExpenseCategory.objects.annotate(
        expense_count=Count('expenses'),
        total_amount=Sum('expenses__amount')
    )
    
    context = {'categories': categories}
    return render(request, 'expenses/category_list.html', context)


@login_required
@group_required(['Admin'])
def category_create(request):
    """Create expense category."""
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría creada exitosamente.')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm()
    
    context = {'form': form, 'title': 'Nueva Categoría'}
    return render(request, 'expenses/category_form.html', context)


@login_required
@group_required(['Admin'])
def category_edit(request, pk):
    """Edit expense category."""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría actualizada exitosamente.')
            return redirect('expenses:category_list')
    else:
        form = ExpenseCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Editar {category.name}'
    }
    return render(request, 'expenses/category_form.html', context)


@login_required
@group_required(['Admin'])
def recurring_list(request):
    """List recurring expenses."""
    recurring = RecurringExpense.objects.select_related('category').filter(is_active=True)
    
    context = {'recurring_expenses': recurring}
    return render(request, 'expenses/recurring_list.html', context)


@login_required
@group_required(['Admin'])
def recurring_create(request):
    """Create recurring expense."""
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto recurrente creado exitosamente.')
            return redirect('expenses:recurring_list')
    else:
        form = RecurringExpenseForm()
    
    context = {'form': form, 'title': 'Nuevo Gasto Recurrente'}
    return render(request, 'expenses/recurring_form.html', context)


@login_required
@group_required(['Admin'])
def expense_report(request):
    """Generate expense report."""
    # Default to current month
    today = timezone.now().date()
    date_from = today.replace(day=1)
    date_to = today
    
    if request.GET.get('date_from'):
        date_from = request.GET.get('date_from')
    if request.GET.get('date_to'):
        date_to = request.GET.get('date_to')
    
    expenses = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to
    )
    
    # Group by category
    by_category = expenses.values(
        'category__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    expense_count = expenses.count()
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'by_category': by_category,
        'total': total,
        'expense_count': expense_count,
        'expenses': expenses,
    }
    return render(request, 'expenses/expense_report.html', context)


# API
@login_required
def api_expenses_by_category(request):
    """API to get expenses grouped by category."""
    expenses = Expense.objects.values(
        'category__name'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')
    
    data = {
        'labels': [e['category__name'] for e in expenses],
        'data': [float(e['total']) for e in expenses],
    }
    
    return JsonResponse(data)
