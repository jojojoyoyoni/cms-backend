from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Case
from apps.audits.models import AuditLog

@receiver(post_save, sender=Case)
def log_case_changes(sender, instance, created, **kwargs):
    # Skip if the case has no organization (shouldn't happen, but safe check)
    if not instance.organization:
        return

    if created:
        AuditLog.objects.create(
            organization=instance.organization,
            user=instance.created_by,
            case=instance,
            action=AuditLog.Action.CREATED,
            changes={'title': instance.title, 'status': instance.status}
        )
    else:
        # If updated, we log the new status (in a full app you'd diff the old values)
        AuditLog.objects.create(
            organization=instance.organization,
            user=instance.created_by, # In a full app, this would be request.user
            case=instance,
            action=AuditLog.Action.UPDATED,
            changes={'status': instance.status}
        )