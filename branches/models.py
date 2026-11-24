from django.db import models


class Branch(models.Model):

    branch_name = models.CharField(max_length=100)

    branch_code = models.CharField(
        max_length=10,
        unique=True
    )

    address = models.TextField()

    phone = models.CharField(max_length=15)

    email = models.EmailField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch_name} ({self.branch_code})"

# Create your models here.
