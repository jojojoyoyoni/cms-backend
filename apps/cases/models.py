from django.db import models
from django.utils import timezone
from apps.users.models import User, Organization, Department

class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        CLOSED = 'CLOSED', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cases')
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='cases')
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_cases')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_cases')
    
    # New Professional Fields
    case_number = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    # case_number = models.CharField(max_length=50, unique=False, blank=True, editable=False)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False) # Soft delete for compliance

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.case_number} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate Case Number (e.g., CASE-2026-0001)
        if not self.case_number:
            prefix = f"CASE-{timezone.now().year}-"
            last_case = Case.objects.filter(case_number__startswith=prefix).order_by('id').last()
            if last_case:
                next_num = int(last_case.case_number.split('-')[-1]) + 1
            else:
                next_num = 1
            self.case_number = f"{prefix}{next_num:04d}"
        super().save(*args, **kwargs)