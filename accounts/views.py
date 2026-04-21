"""
Accounts Views - Login, Dashboard, User Management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import User, Role
from .forms import LoginForm, UserForm, UserEditForm
from decorators.decorators import group_required


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('accounts:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'¡Bienvenido, {user.get_full_name()}!')
                    
                    # Redirect to next URL if provided
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('accounts:home')
                else:
                    messages.error(request, 'Tu cuenta está desactivada. Contactá al administrador.')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos. Verificá tus datos e intentá de nuevo.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('accounts:login')


@login_required
def home_view(request):
    """Dashboard principal - redirige al dashboard."""
    return redirect('accounts:dashboard')


@login_required
def dashboard_view(request):
    """Dashboard principal con estadísticas según el rol del usuario."""
    # Importamos aquí para evitar imports circulares
    from pos.models import POSTransaction
    from stocks.models import Product, ProductCategory
    from cashregister.models import CashShift
    from promotions.models import Promotion
    from django.db import models
    
    user = request.user
    user_groups = list(user.groups.values_list('name', flat=True))
    # Aliases legacy: Manager/Stock Manager → Cajero Manager; General Manager → Admin
    is_admin = (
        user.is_superuser
        or user.is_admin
        or 'Admin' in user_groups
        or 'General Manager' in user_groups
    )
    is_cajero_manager = (
        is_admin
        or 'Cajero Manager' in user_groups
        or 'Manager' in user_groups
        or 'Stock Manager' in user_groups
    )
    is_cashier = is_cajero_manager or 'Cashier' in user_groups
    
    today = timezone.now().date()
    context = {}
    
    # Turno actual del usuario (para cajeros)
    user_shift = CashShift.objects.filter(
        cashier=user,
        status='open'
    ).first()
    context['user_shift'] = user_shift
    
    # === DATOS PARA CAJEROS ===
    if is_cashier or is_cajero_manager or is_admin:
        # Mis ventas del día
        if user_shift:
            my_transactions = POSTransaction.objects.filter(
                session__cash_shift=user_shift,
                status='completed'
            )
            context['my_sales_today'] = my_transactions.aggregate(total=Sum('total'))['total'] or 0
            context['my_transactions_count'] = my_transactions.count()
        else:
            context['my_sales_today'] = 0
            context['my_transactions_count'] = 0
    
    # === DATOS PARA CAJERO MANAGER ===
    if is_cajero_manager or is_admin:
        # Productos con bajo stock
        low_stock_products = Product.objects.filter(
            is_active=True,
            current_stock__lte=models.F('min_stock')
        ).select_related('category')[:10]
        context['low_stock_products'] = low_stock_products
        context['low_stock_count'] = Product.objects.filter(
            is_active=True,
            current_stock__lte=models.F('min_stock')
        ).count()
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['total_categories'] = ProductCategory.objects.filter(is_active=True).count()
    
    # === PERDIDAS DEL MES (merma/vencido/robo/otro) ===
    # Visible para roles de gestion: muestran el impacto real de ajustes de
    # salida en el negocio. Clasificacion por keywords en la nota — sin migracion.
    if is_cajero_manager or is_admin:
        from stocks.models import StockMovement
        from decimal import Decimal
        month_start = today.replace(day=1)
        losses_qs = StockMovement.objects.filter(
            movement_type='adjustment_out',
            created_at__date__gte=month_start,
        ).select_related('product')

        def _classify(ref_text):
            t = (ref_text or '').lower()
            if any(k in t for k in ('vencid', 'expir', 'caduc')):
                return 'expired'
            if 'robo' in t or 'hurto' in t or 'theft' in t:
                return 'theft'
            if 'merma' in t or 'dano' in t or 'daño' in t or 'rotur' in t or 'roto' in t:
                return 'damage'
            return 'other'

        losses_summary = {
            'expired':  {'label': 'Vencidos',   'qty': Decimal('0'), 'amount': Decimal('0'), 'color': '#f39c12', 'icon': 'fa-calendar-times'},
            'theft':    {'label': 'Robo',       'qty': Decimal('0'), 'amount': Decimal('0'), 'color': '#c0392b', 'icon': 'fa-user-secret'},
            'damage':   {'label': 'Merma/Daño', 'qty': Decimal('0'), 'amount': Decimal('0'), 'color': '#e67e22', 'icon': 'fa-triangle-exclamation'},
            'other':    {'label': 'Otros',      'qty': Decimal('0'), 'amount': Decimal('0'), 'color': '#7f8c8d', 'icon': 'fa-question'},
        }
        total_loss_amount = Decimal('0')
        total_loss_qty = Decimal('0')
        for mv in losses_qs:
            bucket = _classify(mv.reference or mv.notes)
            qty_abs = abs(mv.quantity)
            cost_each = mv.product.cost_price or mv.product.purchase_price or Decimal('0')
            amount = qty_abs * cost_each
            losses_summary[bucket]['qty'] += qty_abs
            losses_summary[bucket]['amount'] += amount
            total_loss_qty += qty_abs
            total_loss_amount += amount

        context['losses_summary'] = losses_summary
        context['losses_total_amount'] = total_loss_amount
        context['losses_total_qty'] = total_loss_qty
        context['losses_month_label'] = month_start.strftime('%B %Y').capitalize()

    # === DATOS PARA ADMIN ===
    if is_admin:
        # Ventas del día (global)
        today_transactions = POSTransaction.objects.filter(
            status='completed',
            completed_at__date=today
        )
        context['today_sales'] = today_transactions.aggregate(total=Sum('total'))['total'] or 0
        context['today_transactions'] = today_transactions.count()
        
        # Ventas recientes
        context['recent_sales'] = POSTransaction.objects.filter(
            status='completed'
        ).select_related(
            'session__cash_shift__cash_register',
            'session__cash_shift__cashier'
        ).order_by('-completed_at')[:5]
        
        # Turnos abiertos
        context['open_shifts'] = CashShift.objects.filter(status='open').select_related(
            'cash_register', 'cashier'
        )
        context['open_shifts_count'] = context['open_shifts'].count()
        
        # Promociones activas
        context['active_promotions'] = Promotion.objects.filter(status='active').count()
    
        # Usuarios activos
        context['active_users'] = User.objects.filter(is_active=True).count()
        # Cajas registradas
        from cashregister.models import CashRegister
        context['total_registers'] = CashRegister.objects.filter(is_active=True).count()
    
    return render(request, 'accounts/dashboard.html', context)


@login_required
@group_required(['Admin'])
def user_list(request):
    """Lista de usuarios."""
    users = User.objects.all().prefetch_related('groups')
    # SuperAdmins son invisibles para todos excepto otros superadmins
    if not request.user.is_superuser:
        users = users.filter(is_superuser=False)
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
@group_required(['Admin'])
def user_create(request):
    """Crear nuevo usuario."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Asignar rol
            role_name = form.cleaned_data.get('role')
            if role_name:
                role = Role.objects.get(name=role_name)
                user.groups.add(role)
            
            messages.success(request, f'Usuario {user.username} creado correctamente.')
            return redirect('accounts:user_list')
    else:
        form = UserForm(initial={'is_active': True})
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Crear Usuario',
        'is_edit': False
    })


@login_required
@group_required(['Admin'])
def user_edit(request, pk):
    """Editar usuario."""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            
            # Actualizar rol
            user.groups.clear()
            role_name = form.cleaned_data.get('role')
            if role_name:
                role = Role.objects.get(name=role_name)
                user.groups.add(role)
            
            messages.success(request, f'Usuario {user.username} actualizado correctamente.')
            return redirect('accounts:user_list')
    else:
        initial_role = user.groups.first().name if user.groups.exists() else None
        form = UserEditForm(instance=user, initial={'role': initial_role})
    
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': 'Editar Usuario',
        'is_edit': True
    })


@login_required
@group_required(['Admin'])
def user_delete(request, pk):
    """Eliminar usuario (soft delete)."""
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user.is_active = False
        user.save()
        messages.success(request, f'Usuario {user.username} desactivado correctamente.')
        return redirect('accounts:user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user': user})


@login_required
@group_required(['Admin'])
def user_toggle(request, pk):
    """Activar/desactivar usuario."""
    user = get_object_or_404(User, pk=pk)
    
    if user.pk == request.user.pk:
        messages.error(request, 'No puedes desactivarte a ti mismo.')
    else:
        user.is_active = not user.is_active
        user.save()
        estado = 'activado' if user.is_active else 'desactivado'
        messages.success(request, f'Usuario {user.username} {estado} correctamente.')
    
    return redirect('accounts:user_list')


@login_required
def profile_view(request):
    """Ver y editar perfil propio."""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html')


@login_required
def change_password(request):
    """Cambiar contraseña."""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'La contraseña actual es incorrecta. Verificá e intentá de nuevo.')
        elif new_password != confirm_password:
            messages.error(request, 'Las contraseñas nuevas no coinciden. Asegurate de escribirlas igual.')
        elif len(new_password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, 'Contraseña cambiada correctamente. Por favor inicia sesión nuevamente.')
            return redirect('accounts:login')
    
    return render(request, 'accounts/change_password.html')


# Importar models para usar en home_view
from django.db import models
