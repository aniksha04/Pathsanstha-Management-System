from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from branches.models import Branch
from .models import StaffProfile


class StaffLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )


class StaffCreateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES, required=True)
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(is_active=True), required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            role = self.cleaned_data['role']
            branch = self.cleaned_data['branch'] if role != 'ADMIN' else self.cleaned_data.get('branch')
            StaffProfile.objects.create(user=user, role=role, branch=branch)
        return user


class StaffEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    is_active = forms.BooleanField(required=False)
    role = forms.ChoiceField(choices=StaffProfile.ROLE_CHOICES, required=True)
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(is_active=True), required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'staffprofile'):
            self.fields['role'].initial = self.instance.staffprofile.role
            self.fields['branch'].initial = self.instance.staffprofile.branch

    def save(self, commit=True):
        user = super().save(commit=commit)
        if hasattr(user, 'staffprofile'):
            profile = user.staffprofile
            profile.role = self.cleaned_data['role']
            profile.branch = self.cleaned_data['branch']
            profile.save()
        else:
            StaffProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                branch=self.cleaned_data['branch']
            )
        return user
