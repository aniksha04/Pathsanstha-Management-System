from django import forms
from branches.models import Branch


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['branch_name', 'branch_code', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_branch_code(self):
        code = self.cleaned_data['branch_code'].strip().upper()
        qs = Branch.objects.filter(branch_code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Branch code already exists.")
        return code
