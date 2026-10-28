from django.db import models
from apps.users.models import User, Organization

class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        UPDATED = 'UPDATED', 'Updated'
        DELETED = 'DELETED', 'Deleted'

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    case = models.ForeignKey('cases.Case', on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=Action.choices)
    changes = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on Case {self.case_id} by {self.user}"