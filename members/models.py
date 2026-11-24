from django.db import models

from branches.models import Branch


class Member(models.Model):

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('SUSPENDED', 'Suspended'),
    ]

    member_number = models.CharField(
        max_length=20,
        unique=True
    )

    full_name = models.CharField(max_length=150)

    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    phone = models.CharField(max_length=15)

    email = models.EmailField(
        blank=True,
        null=True
    )

    address = models.TextField()

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name='members'
    )

    joined_date = models.DateField(auto_now_add=True)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.member_number} - {self.full_name}"
# Create your models here.
