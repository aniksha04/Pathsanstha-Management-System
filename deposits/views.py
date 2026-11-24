from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum

from deposits.models import Account, AccountType
from deposits.forms import DepositForm, WithdrawalForm, AccountCreateForm
from deposits.services import deposit_money, withdraw_money
from transactions.models import Transaction
from branches.models import Branch
from accounts.permissions import (
    is_admin,
    is_manager,
    is_accountant,
    can_manage_members,
    filter_by_branch,
    check_branch_access,
    get_user_branch,
)


@login_required
def account_list(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You do not have access to view accounts.")

    accounts = Account.objects.select_related('member', 'account_type', 'branch').all()
    accounts = filter_by_branch(accounts, request.user)

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    type_filter = request.GET.get('type', '').strip()
    branch_filter = request.GET.get('branch', '').strip()

    if search_query:
        accounts = accounts.filter(
            Q(account_number__icontains=search_query) |
            Q(member__full_name__icontains=search_query) |
            Q(member__member_number__icontains=search_query)
        )

    if status_filter:
        accounts = accounts.filter(status=status_filter)

    if type_filter:
        accounts = accounts.filter(account_type_id=type_filter)

    if branch_filter and is_admin(request.user):
        accounts = accounts.filter(branch_id=branch_filter)

    total_balance = accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal("0.00")
    account_types = AccountType.objects.filter(is_active=True)
    branches = Branch.objects.filter(is_active=True) if is_admin(request.user) else None

    return render(request, 'deposits/account_list.html', {
        'accounts': accounts,
        'total_balance': total_balance,
        'account_types': account_types,
        'branches': branches,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'branch_filter': branch_filter,
        'is_manager': is_manager(request.user),
    })


@login_required
def account_create(request):
    if not is_manager(request.user):
        raise PermissionDenied("Only Managers and Admins can open new accounts.")

    member_id = request.GET.get('member')

    if request.method == 'POST':
        form = AccountCreateForm(request.POST, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                account = form.save(commit=False)
                # Ensure branch matches member branch
                account.branch = account.member.branch

                initial_deposit = form.cleaned_data.get('initial_deposit') or Decimal("0.00")
                account.opening_balance = initial_deposit
                account.current_balance = initial_deposit
                account.save()

                if initial_deposit > 0:
                    txn_number = f"DEP-{account.account_number}-000001"
                    Transaction.objects.create(
                        transaction_number=txn_number,
                        account=account,
                        transaction_type='DEPOSIT',
                        amount=initial_deposit,
                        description='Initial account opening deposit',
                        created_by=request.user,
                        status='POSTED'
                    )

            messages.success(request, f"Account {account.account_number} created successfully for {account.member.full_name}!")
            return redirect('account_detail', pk=account.pk)
    else:
        form = AccountCreateForm(user=request.user, member_id=member_id)

    return render(request, 'deposits/account_form.html', {
        'form': form,
        'title': 'Open New Savings / Deposit Account',
    })


@login_required
def account_detail(request, pk):
    account = get_object_or_404(Account.objects.select_related('member', 'branch', 'account_type'), pk=pk)
    check_branch_access(request.user, account)

    transactions = Transaction.objects.filter(account=account).order_by('-created_at')

    return render(request, 'deposits/account_detail.html', {
        'account': account,
        'transactions': transactions,
        'is_manager': is_manager(request.user),
    })


@login_required
def account_toggle_status(request, pk):
    account = get_object_or_404(Account, pk=pk)
    check_branch_access(request.user, account)

    if not is_manager(request.user):
        raise PermissionDenied("Only Managers and Admins can alter account statuses.")

    new_status = request.POST.get('status')
    if new_status in ['ACTIVE', 'FROZEN', 'CLOSED']:
        account.status = new_status
        account.save(update_fields=['status'])
        messages.success(request, f"Account {account.account_number} status set to {new_status}.")

    return redirect('account_detail', pk=account.pk)


@login_required
def deposit_create(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to deposit money.")

    initial_account_id = request.GET.get('account')

    if request.method == 'POST':
        form = DepositForm(request.POST, user=request.user)
        if form.is_valid():
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']

            try:
                deposit_txn = deposit_money(
                    account.id,
                    amount,
                    request.user
                )

                if description:
                    deposit_txn.description = description
                    deposit_txn.save(update_fields=['description'])

                messages.success(
                    request,
                    f'Deposit of ₹{amount} to account {account.account_number} completed successfully!'
                )
                return redirect('transaction_detail', pk=deposit_txn.pk)

            except Exception as e:
                form.add_error(None, str(e))
    else:
        initial_data = {}
        if initial_account_id:
            try:
                acc = Account.objects.get(pk=initial_account_id, status='ACTIVE')
                initial_data['account'] = acc
            except Account.DoesNotExist:
                pass
        form = DepositForm(user=request.user, initial=initial_data)

    return render(request, 'deposits/deposit_form.html', {'form': form})


@login_required
def withdrawal_create(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to withdraw money.")

    initial_account_id = request.GET.get('account')

    if request.method == 'POST':
        form = WithdrawalForm(request.POST, user=request.user)
        if form.is_valid():
            account = form.cleaned_data['account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']

            try:
                withdrawal_txn = withdraw_money(
                    account.id,
                    amount,
                    request.user
                )

                if description:
                    withdrawal_txn.description = description
                    withdrawal_txn.save(update_fields=['description'])

                messages.success(
                    request,
                    f'Withdrawal of ₹{amount} from account {account.account_number} completed successfully!'
                )
                return redirect('transaction_detail', pk=withdrawal_txn.pk)

            except Exception as e:
                form.add_error(None, str(e))
    else:
        initial_data = {}
        if initial_account_id:
            try:
                acc = Account.objects.get(pk=initial_account_id, status='ACTIVE')
                initial_data['account'] = acc
            except Account.DoesNotExist:
                pass
        form = WithdrawalForm(user=request.user, initial=initial_data)

    return render(request, 'deposits/withdrawal_form.html', {'form': form})
