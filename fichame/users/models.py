from django.db import models
from django.contrib.auth.models import  AbstractUser


class User(AbstractUser):
    ROLES_CHOICES = (
        ('trabajador', 'Trabajador'),
        ('empresa', 'Empresa'),
        ('administrador', 'Administrador'),
    )
    role = models.CharField(max_length=20, choices=ROLES_CHOICES, default='trabajador')

    def __str__(self):
        return f"{self.username} ({self.role})"

