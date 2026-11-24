from django import forms
from members.models import Member
from branches.models import Branch
from accounts.permissions import is_admin, get_user_branch


def get_next_member_number():
    """Generates the next unique member number (e.g. MEM005)."""
    last_member = Member.objects.order_by('-id').first()
    if last_member and last_member.member_number:
        digits = ''.join(filter(str.isdigit, last_member.member_number))
        if digits:
            next_num = int(digits) + 1
            return f"MEM{next_num:03d}"
    count = Member.objects.count() + 1
    return f"MEM{count:03d}"


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'member_number',
            'full_name',
            'date_of_birth',
            'gender',
            'phone',
            'email',
            'address',
            'branch',
            'status',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['member_number'].initial = get_next_member_number()

        if user:
            if is_admin(user):
                self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
            else:
                branch = get_user_branch(user)
                if branch:
                    self.fields['branch'].queryset = Branch.objects.filter(pk=branch.pk)
                    self.fields['branch'].initial = branch
                    self.fields['branch'].empty_label = None
                else:
                    self.fields['branch'].queryset = Branch.objects.none()

    def clean_member_number(self):
        number = self.cleaned_data['member_number'].strip().upper()
        qs = Member.objects.filter(member_number=number)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This member number is already assigned.")
        return number


class MemberEditForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'full_name',
            'date_of_birth',
            'gender',
            'phone',
            'email',
            'address',
            'branch',
            'status',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not is_admin(user):
            self.fields['branch'].disabled = True
