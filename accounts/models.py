from django.db import models
from django.contrib.auth.models import User
from branches.models import Branch

class StaffProfile(models.Model):

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('ACCOUNTANT', 'Accountant'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='ACCOUNTANT'
    )
    
    branch = models.ForeignKey(
    Branch,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='staff_members'
)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

# Create your models here.
