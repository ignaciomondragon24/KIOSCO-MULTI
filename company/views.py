"""
Company Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Company, Branch
from .forms import CompanyForm, BranchForm
from decorators.decorators import group_required


@login_required
@group_required(['Admin'])
def company_settings(request):
    """View and edit company settings."""
    company = Company.get_company()
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración guardada exitosamente.')
            return redirect('company:settings')
    else:
        form = CompanyForm(instance=company)
    
    context = {
        'form': form,
        'company': company,
    }
    return render(request, 'company/settings.html', context)


@login_required
@group_required(['Admin'])
def branch_list(request):
    """List all branches."""
    branches = Branch.objects.select_related('company').all()
    
    context = {'branches': branches}
    return render(request, 'company/branch_list.html', context)


@login_required
@group_required(['Admin'])
def branch_create(request):
    """Create a new branch."""
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save(commit=False)
            branch.company = Company.get_company()
            branch.save()
            messages.success(request, 'Sucursal creada exitosamente.')
            return redirect('company:branch_list')
    else:
        form = BranchForm()
    
    context = {'form': form, 'title': 'Nueva Sucursal'}
    return render(request, 'company/branch_form.html', context)


@login_required
@group_required(['Admin'])
def branch_edit(request, pk):
    """Edit a branch."""
    branch = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sucursal actualizada exitosamente.')
            return redirect('company:branch_list')
    else:
        form = BranchForm(instance=branch)
    
    context = {
        'form': form,
        'branch': branch,
        'title': f'Editar {branch.name}'
    }
    return render(request, 'company/branch_form.html', context)


@login_required
@group_required(['Admin'])
def branch_delete(request, pk):
    """Delete a branch."""
    branch = get_object_or_404(Branch, pk=pk)
    
    if request.method == 'POST':
        branch.is_active = False
        branch.save()
        messages.success(request, 'Sucursal desactivada exitosamente.')
        return redirect('company:branch_list')
    
    context = {'branch': branch}
    return render(request, 'company/branch_confirm_delete.html', context)
