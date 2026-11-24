from decimal import Decimal
from django import forms
from django.utils import timezone
from loans.models import Loan, LoanProduct, LoanRepayment, LoanPayment
from members.models import Member
from accounts.permissions import is_admin, get_user_branch


class LoanApplicationForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=Member.objects.filter(status='ACTIVE'),
        label="Select Member"
    )
    loan_product = forms.ModelChoiceField(
        queryset=LoanProduct.objects.filter(is_active=True),
        label="Loan Scheme / Product"
    )
    principal_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("100.00"),
        label="Requested Principal Amount (₹)"
    )
    tenure_months = forms.IntegerField(
        min_value=1,
        max_value=360,
        label="Tenure (Months)"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        member_id = kwargs.pop('member_id', None)
        super().__init__(*args, **kwargs)

        members_qs = Member.objects.filter(status='ACTIVE')
        if user and not is_admin(user):
            branch = get_user_branch(user)
            if branch:
                members_qs = members_qs.filter(branch=branch)
            else:
                members_qs = Member.objects.none()

        self.fields['member'].queryset = members_qs

        if member_id:
            try:
                selected_member = members_qs.get(pk=member_id)
                self.fields['member'].initial = selected_member
            except Member.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('loan_product')
        principal = cleaned_data.get('principal_amount')
        tenure = cleaned_data.get('tenure_months')

        if product and principal:
            if principal < product.min_amount:
                self.add_error('principal_amount', f"Minimum allowed amount for {product.loan_name} is ₹{product.min_amount}.")
            if principal > product.max_amount:
                self.add_error('principal_amount', f"Maximum allowed amount for {product.loan_name} is ₹{product.max_amount}.")

        if product and tenure:
            if tenure > product.max_tenure_months:
                self.add_error('tenure_months', f"Maximum tenure for {product.loan_name} is {product.max_tenure_months} months.")

        return cleaned_data


class LoanDisbursementForm(forms.Form):
    first_due_date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="First EMI Due Date"
    )


class CollectRepaymentForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Payment Amount (₹)"
    )
    payment_mode = forms.ChoiceField(
        choices=LoanPayment.PAYMENT_MODES,
        label="Payment Mode"
    )
    receipt_number = forms.CharField(
        max_length=30,
        label="Receipt / Voucher Number"
    )

    def __init__(self, *args, **kwargs):
        repayment = kwargs.pop('repayment', None)
        super().__init__(*args, **kwargs)

        if repayment:
            remaining_due = repayment.total_due - repayment.amount_paid
            self.fields['amount'].initial = remaining_due
            self.fields['amount'].max_value = remaining_due

            last_payment = LoanPayment.objects.order_by('-id').first()
            seq = (last_payment.id + 1) if last_payment else 1
            self.fields['receipt_number'].initial = f"RCP{seq:05d}"
