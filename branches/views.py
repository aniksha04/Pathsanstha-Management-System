from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count

from branches.models import Branch
from branches.forms import BranchForm
from accounts.permissions import is_admin, admin_required, get_user_branch


@login_required
def branch_list(request):
    if is_admin(request.user):
        branches = Branch.objects.annotate(
            member_count=Count('members', distinct=True),
            account_count=Count('account', distinct=True),
            loan_count=Count('loan', distinct=True),
        ).order_by('branch_code')
    else:
        user_branch = get_user_branch(request.user)
        if not user_branch:
            raise PermissionDenied("You do not have an assigned branch.")
        branches = Branch.objects.filter(pk=user_branch.pk).annotate(
            member_count=Count('members', distinct=True),
            account_count=Count('account', distinct=True),
            loan_count=Count('loan', distinct=True),
        )

    return render(request, 'branches/branch_list.html', {
        'branches': branches,
        'is_admin': is_admin(request.user),
    })


@login_required
@admin_required
def branch_create(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            branch = form.save()
            messages.success(request, f"Branch '{branch.branch_name}' registered successfully!")
            return redirect('branch_list')
    else:
        form = BranchForm()

    return render(request, 'branches/branch_form.html', {
        'form': form,
        'title': 'Open New Society Branch',
        'is_edit': False,
    })


@login_required
def branch_detail(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    
    if not is_admin(request.user):
        user_branch = get_user_branch(request.user)
        if not user_branch or user_branch.pk != branch.pk:
            raise PermissionDenied("You are not authorized to view other branches.")

    staff_members = branch.staff_members.select_related('user').all()
    recent_members = branch.members.order_by('-created_at')[:8]
    
    from deposits.models import Account
    from loans.models import Loan
    from transactions.models import Transaction

    total_deposits = Account.objects.filter(branch=branch).aggregate(Sum('current_balance'))['current_balance__sum'] or 0
    total_loans = Loan.objects.filter(branch=branch).aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
    outstanding_loans = Loan.objects.filter(branch=branch).aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0

    return render(request, 'branches/branch_detail.html', {
        'branch': branch,
        'staff_members': staff_members,
        'recent_members': recent_members,
        'total_deposits': total_deposits,
        'total_loans': total_loans,
        'outstanding_loans': outstanding_loans,
        'is_admin': is_admin(request.user),
    })


@login_required
@admin_required
def branch_edit(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f"Branch '{branch.branch_name}' updated successfully!")
            return redirect('branch_detail', pk=branch.pk)
    else:
        form = BranchForm(instance=branch)

    return render(request, 'branches/branch_form.html', {
        'form': form,
        'branch': branch,
        'title': f'Edit Branch: {branch.branch_name}',
        'is_edit': True,
    })
