"""Escalation service: recipients, creation, auto-resolution, SLA scan pass."""
from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import Case, CaseEscalation
from . import sla as sla_mod

logger = logging.getLogger(__name__)
User = get_user_model()

LEVEL_LABELS = {1: "Level 1 – Team Leader", 2: "Level 2 – Org Admin", 3: "Level 3 – Higher Official"}


# ── notifications wrapper ─────────────────────────────────────────────
# ⚠ CHECK ONCE: open apps/notifications/services.py and make sure the call
# inside _send_one matches your send_notification_to_user() signature.
def _send_one(user, title: str, message: str):
    from apps.notifications.services import send_notification_to_user
    try:
        send_notification_to_user(user, title, message)
    except TypeError:
        send_notification_to_user(user=user, title=title, message=message)


def _notify_users(users, title: str, message: str):
    for u in users:
        try:
            _send_one(u, title, message)
        except Exception:
            logger.exception("SLA notify failed for user %s", getattr(u, "id", "?"))


# ── recipients ────────────────────────────────────────────────────────
def _dept_leader_ids(case) -> list[int]:
    """Best-effort: works with team_leader/leader FKs or membership through-models."""
    dept = getattr(case, "department", None)
    if dept is None:
        return []
    for attr in ("team_leader", "leader", "head"):
        u = getattr(dept, attr, None)
        if u is not None and getattr(u, "pk", None):
            return [u.pk]
    for attr in ("memberships", "department_memberships"):
        mgr = getattr(dept, attr, None)
        if mgr is not None:
            try:
                return [m.user_id for m in mgr.all()
                        if str(getattr(m, "role", "")).upper()
                        in ("TEAM_LEADER", "TEAM_LEAD", "LEADER", "MANAGER")]
            except Exception:
                pass
    return []


def _org_user_ids(org_id, roles) -> list[int]:
    if not org_id:
        return []
    return list(User.objects.filter(
        organization_id=org_id, role__in=roles, is_active=True
    ).values_list("id", flat=True))


def escalation_recipients(case, level: int) -> list:
    ids: list[int] = []
    ids += _dept_leader_ids(case)
    for f in ("assigned_to", "created_by"):
        u = getattr(case, f, None)
        if u is not None and getattr(u, "pk", None):
            ids.append(u.pk)
    if level >= 2:
        ids += _org_user_ids(case.organization_id, ["ORG_ADMIN"])
    if level >= 3:
        ids += _org_user_ids(case.organization_id, ["HIGHER_OFFICIAL"])
    seen, unique = set(), []
    for i in ids:
        if i and i not in seen:
            seen.add(i)
            unique.append(i)
    return list(User.objects.filter(id__in=unique))


# ── creation / resolution ────────────────────────────────────────────
def open_levels(case) -> set[int]:
    return set(CaseEscalation.objects.filter(
        case=case, status=CaseEscalation.Status.OPEN
    ).values_list("level", flat=True))


def create_escalation(case, level: int, source: str, reason: str,
                      note: str = "", created_by=None, notify: bool = True):
    esc = CaseEscalation.objects.create(
        case=case, level=level, source=source, reason=reason,
        note=note or f"SLA breached — escalated to {LEVEL_LABELS[level]}",
        created_by=created_by,
    )
    recipients = escalation_recipients(case, level)
    if recipients:
        esc.notified_users.set(recipients)
    if notify:
        _notify_users(
            recipients,
            f"🚨 [L{level}] Case escalated: {case.case_number}",
            f"{case.title} — {esc.reason}. {esc.note}",
        )
    return esc


def escalate_case(case, source: str = "MANUAL", reason: str = "MANUAL",
                  note: str = "", created_by=None):
    """Create the next available level. Returns (escalation, created)."""
    current = open_levels(case)
    for lvl in (1, 2, 3):
        if lvl not in current:
            return create_escalation(case, lvl, source, reason, note, created_by), True
    top = max(current)
    return CaseEscalation.objects.get(case=case, level=top, status=CaseEscalation.Status.OPEN), False


def auto_resolve_for_case(case, note: str = "Auto-resolved: case closed", user=None):
    return CaseEscalation.objects.filter(
        case=case, status=CaseEscalation.Status.OPEN
    ).update(status=CaseEscalation.Status.RESOLVED,
             resolved_at=timezone.now(), resolved_by=user)


# ── the scan pass (called by the management command) ─────────────────
def run_sla_pass() -> dict:
    stats = {"scanned": 0, "created": [], "auto_resolved": 0}
    now = timezone.now()

    # 1) auto-resolve escalations of closed cases
    closed_qs = CaseEscalation.objects.filter(
        status=CaseEscalation.Status.OPEN, case__status__in=sla_mod.CLOSED_STATUSES
    )
    for esc in closed_qs.select_related("case"):
        auto_resolve_for_case(esc.case)
        stats["auto_resolved"] += 1

    # 2) breach detection
    for case in sla_mod.active_cases_qs().select_related("department", "organization"):
        stats["scanned"] += 1
        info = sla_mod.get_case_sla(case, now=now)
        if not info["is_breached"]:
            continue
        hours_over = -(info["hours_remaining"] or 0)
        target = 3
        if hours_over < sla_mod.ESCALATION_L2_AFTER_HOURS:
            target = 1
        elif hours_over < sla_mod.ESCALATION_L3_AFTER_HOURS:
            target = 2
        current = open_levels(case)
        for lvl in range(1, target + 1):
            if lvl in current:
                continue
            esc = create_escalation(
                case, lvl, source=CaseEscalation.Source.AUTO, reason="SLA_BREACH",
                note=f"SLA breached by {hours_over:.1f}h",
            )
            stats["created"].append({"case": case.case_number, "level": lvl, "id": esc.id})
    return stats