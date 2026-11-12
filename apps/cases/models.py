from django.db import models
from django.utils import timezone
from apps.users.models import User, Organization, Department
from django.conf import settings
from django.db.models import Q

class Case(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
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

     # Approval Workflow Fields
    resolution_notes = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_cases')
    approved_at = models.DateTimeField(null=True, blank=True)
    
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

class CaseDocument(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='case_documents/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.case.case_number}"

class CaseNote(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='case_notes')
    content = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note by {self.author} on {self.case.case_number}"

class Task(models.Model):
    class Status(models.TextChoices):
        TO_DO = 'TO_DO', 'To Do'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        DONE = 'DONE', 'Done'
        BLOCKED = 'BLOCKED', 'Blocked'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TO_DO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.case.case_number})"



class SlaPolicy(models.Model):
    """Resolution SLA per organization + priority. Missing combos fall back to code defaults."""
    # ⚠ use the same model path as Case.organization above
    organization = models.ForeignKey(
        "users.Organization", on_delete=models.CASCADE, related_name="sla_policies"
    )
    priority = models.CharField(max_length=20)  # CRITICAL / HIGH / MEDIUM / LOW
    resolution_hours = models.PositiveIntegerField()
    first_response_hours = models.PositiveIntegerField(null=True, blank=True)
    at_risk_pct = models.PositiveIntegerField(default=75)  # % of window consumed → AT_RISK
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "priority")
        ordering = ["organization", "priority"]

    def __str__(self):
        return f"{self.organization} · {self.priority} · {self.resolution_hours}h"


class CaseEscalation(models.Model):
    class Level(models.IntegerChoices):
        L1 = 1, "Level 1 – Team Leader"
        L2 = 2, "Level 2 – Org Admin"
        L3 = 3, "Level 3 – Higher Official"

    class Source(models.TextChoices):
        AUTO = "AUTO", "Automatic (SLA breach)"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        RESOLVED = "RESOLVED", "Resolved"

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="escalations")
    level = models.PositiveSmallIntegerField(choices=Level.choices, default=1)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.AUTO)
    reason = models.CharField(max_length=50, default="SLA_BREACH")
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="escalations_created",
    )
    notified_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="escalations_notified")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="escalations_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "level"], condition=Q(status="OPEN"),
                name="unique_open_escalation_per_level",
            )
        ]

    def __str__(self):
        return f"[L{self.level}] {self.case.case_number} ({self.status})"