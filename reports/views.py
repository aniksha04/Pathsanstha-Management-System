import json
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from loans.models import Loan, LoanRepayment, LoanPayment, LoanProduct
from members.models import Member
from deposits.models import Account
from transactions.models import Transaction
from branches.models import Branch
from accounts.permissions import (
    is_accountant,
    is_admin,
    filter_by_branch,
    get_user_branch,
)


@login_required
def dashboard(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to view the management dashboard.")

    user = request.user
    admin_user = is_admin(user)
    user_branch = get_user_branch(user)

    # Base querysets scoped by branch
    members_qs = filter_by_branch(Member.objects.all(), user)
    accounts_qs = filter_by_branch(Account.objects.all(), user)
    loans_qs = filter_by_branch(Loan.objects.all(), user)

    # Transactions scoping
    if admin_user:
        transactions_qs = Transaction.objects.all()
    else:
        transactions_qs = Transaction.objects.filter(
            Q(account__branch=user_branch) |
            Q(loan_payment__loan__branch=user_branch)
        )

    # Core Financial Metrics
    total_members = members_qs.count()
    total_active_accounts = accounts_qs.filter(status='ACTIVE').count()
    available_account_balance = accounts_qs.aggregate(Sum('current_balance'))['current_balance__sum'] or Decimal("0.00")

    total_deposits = transactions_qs.filter(
        transaction_type='DEPOSIT',
        status='POSTED'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

    total_withdrawals = transactions_qs.filter(
        transaction_type='WITHDRAWAL',
        status='POSTED'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

    total_loan_amount = loans_qs.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal("0.00")
    outstanding_loan_balance = loans_qs.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or Decimal("0.00")

    total_repayments = transactions_qs.filter(
        transaction_type='LOAN_REPAYMENT',
        status='POSTED'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")

    # Recent Transactions & Members
    recent_transactions = transactions_qs.select_related(
        'account__member',
        'loan_payment__loan__member'
    ).order_by('-created_at')[:6]

    recent_members = members_qs.select_related('branch').order_by('-created_at')[:5]

    # Monthly Trends Data (Last 6 months)
    months_labels = []
    monthly_deposits = []
    monthly_withdrawals = []

    now = timezone.now()
    for i in range(5, -1, -1):
        # Calculate start and end of target month
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1

        month_label = timezone.datetime(year, month, 1).strftime('%b %Y')
        months_labels.append(month_label)

        dep_sum = transactions_qs.filter(
            transaction_type='DEPOSIT',
            status='POSTED',
            created_at__year=year,
            created_at__month=month
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        wdr_sum = transactions_qs.filter(
            transaction_type='WITHDRAWAL',
            status='POSTED',
            created_at__year=year,
            created_at__month=month
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        monthly_deposits.append(float(dep_sum))
        monthly_withdrawals.append(float(wdr_sum))

    # Loan Status Distribution
    loan_statuses = ['PENDING', 'APPROVED', 'DISBURSED', 'CLOSED', 'REJECTED']
    loan_status_counts = []
    for st in loan_statuses:
        cnt = loans_qs.filter(status=st).count()
        loan_status_counts.append(cnt)

    # Branch-wise Overview (ADMIN only)
    branch_overview = []
    if admin_user:
        all_branches = Branch.objects.filter(is_active=True).order_by('branch_code')
        for b in all_branches:
            b_members = Member.objects.filter(branch=b).count()
            b_accounts = Account.objects.filter(branch=b, status='ACTIVE').count()
            b_deposits = Account.objects.filter(branch=b).aggregate(Sum('current_balance'))['current_balance__sum'] or 0
            b_loans = Loan.objects.filter(branch=b).aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
            b_outstanding = Loan.objects.filter(branch=b).aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0

            branch_overview.append({
                'branch': b,
                'members': b_members,
                'accounts': b_accounts,
                'deposits': b_deposits,
                'loans': b_loans,
                'outstanding': b_outstanding,
            })

    context = {
        'total_members': total_members,
        'total_active_accounts': total_active_accounts,
        'available_account_balance': available_account_balance,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_loan_amount': total_loan_amount,
        'outstanding_loan_balance': outstanding_loan_balance,
        'total_repayments': total_repayments,
        'recent_transactions': recent_transactions,
        'recent_members': recent_members,
        'months_labels_json': json.dumps(months_labels),
        'monthly_deposits_json': json.dumps(monthly_deposits),
        'monthly_withdrawals_json': json.dumps(monthly_withdrawals),
        'loan_status_counts_json': json.dumps(loan_status_counts),
        'branch_overview': branch_overview,
        'is_admin': admin_user,
    }

    return render(request, 'reports/dashboard.html', context)


@login_required
def loan_summary(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to view financial reports.")

    user = request.user
    loans_qs = filter_by_branch(Loan.objects.all(), user)

    total_loans = loans_qs.count()
    approved_loans = loans_qs.filter(status='APPROVED').count()
    disbursed_loans = loans_qs.filter(status='DISBURSED').count()
    closed_loans = loans_qs.filter(status='CLOSED').count()
    pending_loans = loans_qs.filter(status='PENDING').count()

    total_principal = loans_qs.aggregate(Sum('principal_amount'))['principal_amount__sum'] or 0
    total_outstanding = loans_qs.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or 0

    product_summary = LoanProduct.objects.filter(is_active=True).annotate(
        count=Count('loan'),
        total_amount=Sum('loan__principal_amount')
    )

    overdue_count = LoanRepayment.objects.filter(
        loan__in=loans_qs,
        status__in=['PENDING', 'PARTIAL'],
        due_date__lt=timezone.localdate()
    ).count()

    context = {
        'total_loans': total_loans,
        'approved_loans': approved_loans,
        'disbursed_loans': disbursed_loans,
        'closed_loans': closed_loans,
        'pending_loans': pending_loans,
        'total_principal': total_principal,
        'total_outstanding': total_outstanding,
        'product_summary': product_summary,
        'overdue_count': overdue_count,
    }

    return render(request, 'reports/loan_summary.html', context)
