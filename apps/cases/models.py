from django.db import models
from apps.users.models import User, Organization, Department

class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        CLOSED = 'CLOSED', 'Closed'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cases')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='cases')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_cases')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_cases')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"