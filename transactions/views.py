from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum

from transactions.models import Transaction
from accounts.permissions import (
    is_admin,
    is_accountant,
    filter_by_branch,
    check_branch_access,
    get_user_branch,
)
from branches.models import Branch


@login_required
def transaction_list(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to view transactions.")

    txns = Transaction.objects.select_related('account__member', 'account__branch', 'created_by', 'loan_payment__loan').all()

    # Scope by branch
    if not is_admin(request.user):
        user_branch = get_user_branch(request.user)
        if not user_branch:
            raise PermissionDenied("You do not have an assigned branch.")
        txns = txns.filter(
            Q(account__branch=user_branch) |
            Q(loan_payment__loan__branch=user_branch)
        )

    search_query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search_query:
        txns = txns.filter(
            Q(transaction_number__icontains=search_query) |
            Q(account__account_number__icontains=search_query) |
            Q(account__member__full_name__icontains=search_query) |
            Q(loan_payment__loan__loan_number__icontains=search_query) |
            Q(loan_payment__receipt_number__icontains=search_query)
        )

    if type_filter:
        txns = txns.filter(transaction_type=type_filter)

    if date_from:
        txns = txns.filter(created_at__date__gte=date_from)
    if date_to:
        txns = txns.filter(created_at__date__lte=date_to)

    total_amount = txns.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'transactions/transaction_list.html', {
        'transactions': txns,
        'total_amount': total_amount,
        'search_query': search_query,
        'type_filter': type_filter,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': Transaction.TRANSACTION_TYPES,
    })


@login_required
def transaction_detail(request, pk):
    txn = get_object_or_404(
        Transaction.objects.select_related(
            'account__member__branch',
            'created_by',
            'loan_payment__loan__member__branch',
            'loan_payment__received_by'
        ),
        pk=pk
    )

    # Check branch access
    if not is_admin(request.user):
        user_branch = get_user_branch(request.user)
        txn_branch = None
        if txn.account and txn.account.branch:
            txn_branch = txn.account.branch
        elif txn.loan_payment and txn.loan_payment.loan.branch:
            txn_branch = txn.loan_payment.loan.branch

        if txn_branch and txn_branch.id != user_branch.id:
            raise PermissionDenied("You are not authorized to view this transaction.")

    return render(request, 'transactions/transaction_detail.html', {
        'transaction': txn,
    })
