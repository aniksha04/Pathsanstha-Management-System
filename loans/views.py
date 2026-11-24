from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Sum
from django.utils import timezone

from loans.models import Loan, LoanProduct, LoanRepayment, LoanPayment
from loans.forms import LoanApplicationForm, LoanDisbursementForm, CollectRepaymentForm
from loans.services import (
    apply_for_loan,
    approve_loan,
    reject_loan,
    disburse_loan,
    generate_emi_schedule,
    collect_emi_payment,
    add_months,
)
from accounts.permissions import (
    is_admin,
    is_manager,
    is_accountant,
    can_approve_loans,
    can_disburse_loans,
    filter_by_branch,
    check_branch_access,
    get_user_branch,
)
from branches.models import Branch


@login_required
def loan_list(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You do not have permission to view loans.")

    loans = Loan.objects.select_related('member', 'loan_product', 'branch', 'approved_by').all()
    loans = filter_by_branch(loans, request.user)

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    product_filter = request.GET.get('product', '').strip()
    branch_filter = request.GET.get('branch', '').strip()

    if search_query:
        loans = loans.filter(
            Q(loan_number__icontains=search_query) |
            Q(member__full_name__icontains=search_query) |
            Q(member__member_number__icontains=search_query)
        )

    if status_filter:
        loans = loans.filter(status=status_filter)

    if product_filter:
        loans = loans.filter(loan_product_id=product_filter)

    if branch_filter and is_admin(request.user):
        loans = loans.filter(branch_id=branch_filter)

    total_portfolio = loans.aggregate(Sum('principal_amount'))['principal_amount__sum'] or Decimal("0.00")
    total_outstanding = loans.aggregate(Sum('outstanding_balance'))['outstanding_balance__sum'] or Decimal("0.00")

    loan_products = LoanProduct.objects.filter(is_active=True)
    branches = Branch.objects.filter(is_active=True) if is_admin(request.user) else None

    return render(request, 'loans/loan_list.html', {
        'loans': loans,
        'total_portfolio': total_portfolio,
        'total_outstanding': total_outstanding,
        'loan_products': loan_products,
        'branches': branches,
        'search_query': search_query,
        'status_filter': status_filter,
        'product_filter': product_filter,
        'branch_filter': branch_filter,
        'can_approve_loans': can_approve_loans(request.user),
    })


@login_required
def loan_apply(request):
    if not is_accountant(request.user):
        raise PermissionDenied("You do not have permission to initiate loan applications.")

    member_id = request.GET.get('member')

    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, user=request.user)
        if form.is_valid():
            member = form.cleaned_data['member']
            product = form.cleaned_data['loan_product']
            principal = form.cleaned_data['principal_amount']
            tenure = form.cleaned_data['tenure_months']

            try:
                loan = apply_for_loan(member, product, principal, tenure, request.user)
                messages.success(request, f"Loan application {loan.loan_number} for ₹{principal} submitted successfully!")
                return redirect('loan_detail', pk=loan.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = LoanApplicationForm(user=request.user, member_id=member_id)

    return render(request, 'loans/loan_apply.html', {'form': form})


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(
        Loan.objects.select_related('member', 'loan_product', 'branch', 'approved_by'),
        pk=pk
    )
    check_branch_access(request.user, loan)

    repayments = loan.repayments.all().order_by('installment_number')
    payments = loan.payments.select_related('received_by').all().order_by('-payment_date')

    # Disbursement form
    disbursement_form = LoanDisbursementForm(initial={'first_due_date': add_months(timezone.localdate(), 1)})

    return render(request, 'loans/loan_detail.html', {
        'loan': loan,
        'repayments': repayments,
        'payments': payments,
        'disbursement_form': disbursement_form,
        'can_approve': can_approve_loans(request.user),
        'can_disburse': can_disburse_loans(request.user),
    })


@login_required
def loan_approve(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    check_branch_access(request.user, loan)

    if not can_approve_loans(request.user):
        raise PermissionDenied("Only Managers and Admins can approve loans.")

    if request.method == 'POST':
        try:
            approve_loan(loan, request.user)
            messages.success(request, f"Loan {loan.loan_number} has been officially approved.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect('loan_detail', pk=loan.pk)


@login_required
def loan_reject(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    check_branch_access(request.user, loan)

    if not can_approve_loans(request.user):
        raise PermissionDenied("Only Managers and Admins can reject loans.")

    if request.method == 'POST':
        try:
            reject_loan(loan, request.user)
            messages.warning(request, f"Loan {loan.loan_number} has been rejected.")
        except Exception as e:
            messages.error(request, str(e))

    return redirect('loan_detail', pk=loan.pk)


@login_required
def loan_disburse(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    check_branch_access(request.user, loan)

    if not can_disburse_loans(request.user):
        raise PermissionDenied("Only Managers and Admins can disburse loans.")

    if request.method == 'POST':
        form = LoanDisbursementForm(request.POST)
        if form.is_valid():
            first_due_date = form.cleaned_data['first_due_date']
            try:
                # Disburse loan into savings account & post ledger transaction
                disburse_loan(loan, request.user)
                # Generate EMI repayment schedule
                generate_emi_schedule(loan, first_due_date, request.user)
                messages.success(
                    request,
                    f"Loan {loan.loan_number} (₹{loan.principal_amount}) disbursed successfully! Repayment schedule generated."
                )
            except Exception as e:
                messages.error(request, f"Disbursement error: {str(e)}")
        else:
            messages.error(request, "Invalid first due date selected.")

    return redirect('loan_detail', pk=loan.pk)


@login_required
def loan_collect_payment(request, pk, repayment_id):
    loan = get_object_or_404(Loan, pk=pk)
    check_branch_access(request.user, loan)

    repayment = get_object_or_404(LoanRepayment, pk=repayment_id, loan=loan)

    if not is_accountant(request.user):
        raise PermissionDenied("You are not authorized to collect payments.")

    if request.method == 'POST':
        form = CollectRepaymentForm(request.POST, repayment=repayment)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payment_mode = form.cleaned_data['payment_mode']
            receipt_number = form.cleaned_data['receipt_number']

            try:
                payment = collect_emi_payment(
                    loan=loan,
                    repayment=repayment,
                    amount=amount,
                    payment_mode=payment_mode,
                    receipt_number=receipt_number,
                    staff_user=request.user
                )
                messages.success(request, f"Repayment of ₹{amount} received under Receipt #{receipt_number}!")
                return redirect('loan_receipt', payment_id=payment.pk)
            except Exception as e:
                form.add_error(None, str(e))
    else:
        form = CollectRepaymentForm(repayment=repayment)

    return render(request, 'loans/repay_form.html', {
        'loan': loan,
        'repayment': repayment,
        'form': form,
    })


@login_required
def loan_receipt(request, payment_id):
    payment = get_object_or_404(
        LoanPayment.objects.select_related('loan__member__branch', 'loan__loan_product', 'repayment', 'received_by'),
        pk=payment_id
    )
    check_branch_access(request.user, payment.loan)

    return render(request, 'loans/receipt.html', {
        'payment': payment,
        'loan': payment.loan,
    })
