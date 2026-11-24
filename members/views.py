from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from members.models import Member
from members.form import MemberForm, MemberEditForm
from accounts.permissions import (
    is_admin,
    is_manager,
    is_accountant,
    can_manage_members,
    filter_by_branch,
    check_branch_access,
    get_user_branch,
)
from deposits.models import Account
from loans.models import Loan
from transactions.models import Transaction
from branches.models import Branch


@login_required
def member_list(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You do not have access to view members.")

    members = Member.objects.select_related('branch').all()
    members = filter_by_branch(members, request.user)

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    branch_filter = request.GET.get('branch', '').strip()

    if search_query:
        members = members.filter(
            Q(member_number__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    if status_filter:
        members = members.filter(status=status_filter)

    if branch_filter and is_admin(request.user):
        members = members.filter(branch_id=branch_filter)

    branches = Branch.objects.filter(is_active=True) if is_admin(request.user) else None

    return render(request, 'members/member_list.html', {
        'members': members,
        'search_query': search_query,
        'status_filter': status_filter,
        'branch_filter': branch_filter,
        'branches': branches,
        'can_manage_members': can_manage_members(request.user),
    })


@login_required
def member_register(request):
    if not can_manage_members(request.user):
        messages.error(request, 'Accountants are not authorized to register members.')
        return redirect('member_list')

    if request.method == 'POST':
        form = MemberForm(request.POST, user=request.user)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Member {member.full_name} ({member.member_number}) registered successfully!')
            return redirect('member_detail', pk=member.pk)
    else:
        form = MemberForm(user=request.user)

    return render(request, 'members/member_register.html', {'form': form})


@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related('branch'), pk=pk)
    check_branch_access(request.user, member)

    # Member's accounts
    accounts = Account.objects.filter(member=member).select_related('account_type')
    account_ids = accounts.values_list('id', flat=True)

    # Member's deposits and withdrawals
    deposits = Transaction.objects.filter(
        account_id__in=account_ids,
        transaction_type='DEPOSIT'
    ).order_by('-created_at')[:10]

    withdrawals = Transaction.objects.filter(
        account_id__in=account_ids,
        transaction_type='WITHDRAWAL'
    ).order_by('-created_at')[:10]

    all_transactions = Transaction.objects.filter(
        account_id__in=account_ids
    ).order_by('-created_at')[:15]

    # Member's loans
    loans = Loan.objects.filter(member=member).select_related('loan_product').order_by('-applied_at')

    return render(request, 'members/member_detail.html', {
        'member': member,
        'accounts': accounts,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'all_transactions': all_transactions,
        'loans': loans,
        'can_manage_members': can_manage_members(request.user),
    })


@login_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    check_branch_access(request.user, member)

    if not can_manage_members(request.user):
        raise PermissionDenied("You are not authorized to edit member records.")

    if request.method == 'POST':
        form = MemberEditForm(request.POST, instance=member, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Member '{member.full_name}' updated successfully!")
            return redirect('member_detail', pk=member.pk)
    else:
        form = MemberEditForm(instance=member, user=request.user)

    return render(request, 'members/member_edit.html', {
        'form': form,
        'member': member,
    })


@login_required
def member_toggle_status(request, pk):
    member = get_object_or_404(Member, pk=pk)
    check_branch_access(request.user, member)

    if not can_manage_members(request.user):
        raise PermissionDenied("You are not authorized to change member status.")

    new_status = request.POST.get('status')
    if new_status in ['ACTIVE', 'INACTIVE', 'SUSPENDED']:
        member.status = new_status
        member.save(update_fields=['status'])
        messages.success(request, f"Member status updated to {new_status}.")

    return redirect('member_detail', pk=member.pk)
