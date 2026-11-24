from decimal import Decimal
from django import forms
from deposits.models import Account, AccountType
from members.models import Member
from branches.models import Branch
from accounts.permissions import is_admin, get_user_branch


def get_next_account_number():
    last_account = Account.objects.order_by('-id').first()
    if last_account and last_account.account_number:
        digits = ''.join(filter(str.isdigit, last_account.account_number))
        if digits:
            next_num = int(digits) + 1
            return f"ACC{next_num:03d}"
    count = Account.objects.count() + 1
    return f"ACC{count:03d}"


class AccountCreateForm(forms.ModelForm):
    initial_deposit = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        initial=Decimal("0.00"),
        label="Initial Deposit (₹)",
        required=False,
    )

    class Meta:
        model = Account
        fields = ['account_number', 'member', 'account_type', 'initial_deposit', 'status']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        member_id = kwargs.pop('member_id', None)
        super().__init__(*args, **kwargs)

        self.fields['account_number'].initial = get_next_account_number()

        # Scope members according to RBAC
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


class DepositForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(status='ACTIVE'),
        label="Select Account"
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Deposit Amount (₹)"
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional transaction notes...'}),
        label="Description / Remarks"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not is_admin(user):
            branch = get_user_branch(user)
            if branch:
                self.fields['account'].queryset = self.fields['account'].queryset.filter(branch=branch)
            else:
                self.fields['account'].queryset = Account.objects.none()


class WithdrawalForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(status='ACTIVE'),
        label="Select Account"
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("1.00"),
        label="Withdrawal Amount (₹)"
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional transaction notes...'}),
        label="Description / Remarks"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not is_admin(user):
            branch = get_user_branch(user)
            if branch:
                self.fields['account'].queryset = self.fields['account'].queryset.filter(branch=branch)
            else:
                self.fields['account'].queryset = Account.objects.none()
