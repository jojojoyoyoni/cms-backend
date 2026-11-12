"""SLA computation. All tunables live here — no settings.py changes needed."""
from __future__ import annotations

from datetime import date, datetime, time

from django.core.exceptions import FieldDoesNotExist
from django.utils import timezone

from .models import Case, SlaPolicy

# ─── EDIT IF YOUR CHOICES DIFFER ───────────────────────────
CLOSED_STATUSES = {"CLOSED"}
PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
DEFAULT_SLA_HOURS = {"CRITICAL": 4, "HIGH": 24, "MEDIUM": 72, "LOW": 168}
AT_RISK_PCT_DEFAULT = 75
ESCALATION_L2_AFTER_HOURS = 24
ESCALATION_L3_AFTER_HOURS = 48
# ───────────────────────────────────────────────────────────


def _has_field(model, name: str) -> bool:
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


HAS_CLOSED_AT = _has_field(Case, "closed_at")      # used only if you add it later
HAS_IS_DELETED = _has_field(Case, "is_deleted")


def get_policy(organization_id, priority: str):
    if organization_id is None:
        return None
    return SlaPolicy.objects.filter(
        organization_id=organization_id, priority=priority
    ).first()


def get_resolution_hours(case) -> tuple[float, int]:
    """(hours, at_risk_pct) from org policy, falling back to defaults."""
    pol = get_policy(getattr(case, "organization_id", None), case.priority)
    if pol and pol.resolution_hours:
        return float(pol.resolution_hours), int(pol.at_risk_pct or AT_RISK_PCT_DEFAULT)
    return float(DEFAULT_SLA_HOURS.get(case.priority, 72)), AT_RISK_PCT_DEFAULT


def _deadline(case):
    """due_date may be a date or datetime — normalize to tz-aware datetime."""
    d = case.due_date
    if d is None:
        return None
    if isinstance(d, datetime):
        return timezone.make_aware(d) if timezone.is_naive(d) else d
    if isinstance(d, date):
        return timezone.make_aware(datetime.combine(d, time(23, 59, 59)))
    return None


def active_cases_qs():
    qs = Case.objects.all()
    if HAS_IS_DELETED:
        qs = qs.filter(is_deleted=False)
    return qs.exclude(status__in=CLOSED_STATUSES)


def get_case_sla(case, now=None) -> dict:
    now = now or timezone.now()
    deadline = _deadline(case)
    hours, at_risk_pct = get_resolution_hours(case)

    out = {
        "state": "NO_DUE_DATE", "is_breached": False,
        "hours_remaining": None, "hours_total": hours,
        "hours_elapsed_pct": None, "at_risk_pct": at_risk_pct,
        "due_date": deadline.isoformat() if deadline else None,
    }
    if case.status in CLOSED_STATUSES:
        out["state"] = "CLOSED"
        if HAS_CLOSED_AT and getattr(case, "closed_at", None) and deadline:
            out["state"] = "MET" if case.closed_at <= deadline else "CLOSED_LATE"
        return out
    if deadline is None:
        return out

    remaining = (deadline - now).total_seconds() / 3600.0
    out["hours_remaining"] = round(remaining, 1)
    out["is_breached"] = remaining < 0

    if remaining < 0:
        out["state"] = "BREACHED"
        return out

    created = getattr(case, "created_at", None) or getattr(case, "created", None)
    if created:
        started = timezone.make_aware(created) if timezone.is_naive(created) else created
        total_secs = max((deadline - started).total_seconds(), 1)
        pct = ((now - started).total_seconds() / total_secs) * 100
        out["hours_elapsed_pct"] = round(pct, 1)
        out["state"] = "AT_RISK" if pct >= at_risk_pct else "ON_TRACK"
    else:
        # no created_at field → approximate: <25% of the SLA window left = at risk
        out["state"] = "AT_RISK" if remaining <= hours * 0.25 else "ON_TRACK"
    return out