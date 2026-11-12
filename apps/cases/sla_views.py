"""SLA + escalation API endpoints (plain APIViews, inline permission checks)."""
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Case, CaseEscalation, SlaPolicy
from . import sla as sla_mod
from .escalation import auto_resolve_for_case, escalate_case

MANAGE_ROLES = ("ORG_ADMIN", "TEAM_LEADER", "HIGHER_OFFICIAL")


def _forbidden():
    return Response({"detail": "Not allowed for your role."}, status=status.HTTP_403_FORBIDDEN)


def _same_org(user, case) -> bool:
    return user.organization_id is not None and user.organization_id == case.organization_id


def _case_brief(case) -> dict:
    dept = getattr(case, "department", None)
    return {
        "id": case.id, "case_number": case.case_number, "title": case.title,
        "status": case.status, "priority": case.priority,
        "department": getattr(dept, "name", None),
        "sla_state": sla_mod.get_case_sla(case)["state"],
    }


def _esc_dict(esc: CaseEscalation) -> dict:
    return {
        "id": esc.id, "level": esc.level,
        "level_display": esc.get_level_display(),
        "source": esc.source, "reason": esc.reason, "note": esc.note,
        "status": esc.status, "created_at": esc.created_at,
        "resolved_at": esc.resolved_at,
        "created_by": getattr(esc.created_by, "get_full_name", lambda: None)()
                      or getattr(esc.created_by, "username", None),
        "case": _case_brief(esc.case),
    }


def visible_escalations(user):
    """Role-scoped queryset of escalations."""
    qs = CaseEscalation.objects.select_related("case", "case__department")
    if user.role == "SUPERADMIN":
        return qs.none()
    if user.role in ("ORG_ADMIN", "HIGHER_OFFICIAL"):
        return qs.filter(case__organization_id=user.organization_id)
    if user.role == "TEAM_LEADER":
        return qs.filter(
            Q(case__organization_id=user.organization_id),
            Q(case__department_id=getattr(user, "department_id", None))
            | Q(case__assigned_to=user) | Q(case__created_by=user),
        )
    return qs.filter(Q(case__assigned_to=user) | Q(case__created_by=user))


def _get_visible_case(user, pk) -> Case:
    case = get_object_or_404(Case, pk=pk)
    if user.role == "SUPERADMIN" or not _same_org(user, case):
        raise PermissionError
    return case


class CaseSlaView(APIView):
    """GET /api/cases/<id>/sla/ — authoritative SLA state for one case."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        try:
            case = _get_visible_case(request.user, pk)
        except PermissionError:
            return _forbidden()
        data = sla_mod.get_case_sla(case)
        data["open_escalations"] = CaseEscalation.objects.filter(
            case=case, status=CaseEscalation.Status.OPEN
        ).count()
        pol = sla_mod.get_policy(case.organization_id, case.priority)
        data["policy_hours"] = pol.resolution_hours if pol else \
            sla_mod.DEFAULT_SLA_HOURS.get(case.priority)
        return Response(data)


class CaseEscalateView(APIView):
    """POST /api/cases/<id>/escalate/  body: {"note": "...", "reason": "..."}"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        try:
            case = _get_visible_case(request.user, pk)
        except PermissionError:
            return _forbidden()
        u = request.user
        allowed = u.role in MANAGE_ROLES or (
            u.role == "ANALYST" and
            (case.assigned_to_id == u.id or case.created_by_id == u.id)
        )
        if not allowed:
            return _forbidden()
        esc, created = escalate_case(
            case, source=CaseEscalation.Source.MANUAL,
            reason=request.data.get("reason", "MANUAL"),
            note=request.data.get("note", ""), created_by=u,
        )
        return Response(
            {**_esc_dict(esc), "created": created},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SlaPolicyListCreateView(APIView):
    """GET: list org policies (auto-seeds defaults). POST/PUT: upsert (ORG_ADMIN only)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        if u.role == "SUPERADMIN":
            return _forbidden()
        for pr in sla_mod.PRIORITIES:
            SlaPolicy.objects.get_or_create(
                organization_id=u.organization_id, priority=pr,
                defaults={"resolution_hours": sla_mod.DEFAULT_SLA_HOURS.get(pr, 72)},
            )
        can_edit = (u.role == "ORG_ADMIN")
        data = [{
            "id": p.id, "priority": p.priority,
            "resolution_hours": p.resolution_hours,
            "first_response_hours": p.first_response_hours,
            "at_risk_pct": p.at_risk_pct,
            "can_edit": can_edit,
        } for p in SlaPolicy.objects.filter(organization_id=u.organization_id)]
        return Response(data)
    
    def post(self, request):
        u = request.user
        if u.role != "ORG_ADMIN":
            return _forbidden()
        pr = request.data.get("priority")
        if pr not in sla_mod.PRIORITIES:
            return Response({"detail": f"priority must be one of {sla_mod.PRIORITIES}"},
                            status=status.HTTP_400_BAD_REQUEST)
        pol, _ = SlaPolicy.objects.update_or_create(
            organization_id=u.organization_id, priority=pr,
            defaults={
                "resolution_hours": int(request.data.get("resolution_hours", 72)),
                "first_response_hours": request.data.get("first_response_hours"),
                "at_risk_pct": int(request.data.get("at_risk_pct", 75)),
            },
        )
        return Response({"id": pol.id, "priority": pol.priority,
                         "resolution_hours": pol.resolution_hours},
                        status=status.HTTP_201_CREATED)


class EscalationListView(APIView):
    """GET /api/escalations/?resolved=false&case=<id>&level=2"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = visible_escalations(request.user)
        resolved = request.query_params.get("resolved")
        if resolved is not None:
            wanted = CaseEscalation.Status.RESOLVED if resolved.lower() in ("true", "1") \
                else CaseEscalation.Status.OPEN
            qs = qs.filter(status=wanted)
        case_id = request.query_params.get("case")
        if case_id:
            qs = qs.filter(case_id=case_id)
        if request.query_params.get("level"):
            qs = qs.filter(level=int(request.query_params["level"]))
        return Response([_esc_dict(e) for e in qs[:100]])
    
class EscalationSummaryView(APIView):
    """GET /api/escalations/summary/ — badge + dashboard counts."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        qs = visible_escalations(u)
        open_qs = qs.filter(status=CaseEscalation.Status.OPEN)
        breached_count = open_qs.values("case_id").distinct().count()

        # total open cases in scope (for compliance %)
        base = Case.objects.all()
        if sla_mod.HAS_IS_DELETED:
            base = base.filter(is_deleted=False)
        base = base.exclude(status__in=sla_mod.CLOSED_STATUSES)
        if u.role == "SUPERADMIN":
            base = base.none()
        elif u.role in ("ORG_ADMIN", "HIGHER_OFFICIAL"):
            base = base.filter(organization_id=u.organization_id)
        elif u.role == "TEAM_LEADER":
            base = base.filter(
                Q(organization_id=u.organization_id),
                Q(department_id=getattr(u, "department_id", None))
                | Q(assigned_to=u) | Q(created_by=u),
            )
        else:  # ANALYST
            base = base.filter(Q(assigned_to=u) | Q(created_by=u))
        total_open = base.count()
        compliance_pct = round(100 * (total_open - breached_count) / total_open, 1) if total_open else 100.0

        return Response({
            "open": open_qs.count(),
            "by_level": {f"L{k}": open_qs.filter(level=k).count() for k in (1, 2, 3)},
            "breached_cases": breached_count,
            "total_open_cases": total_open,
            "compliance_pct": compliance_pct,
        })

class EscalationResolveView(APIView):
    """POST /api/escalations/<id>/resolve/  body: {"note": "..."}"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        esc = get_object_or_404(
            CaseEscalation.select_related if False else CaseEscalation.objects.select_related("case"),
            pk=pk,
        )
        u = request.user
        can = (
            u.role in MANAGE_ROLES and _same_org(u, esc.case)
        ) or esc.case.assigned_to_id == u.id
        if not can:
            return _forbidden()
        if esc.status == CaseEscalation.Status.OPEN:
            esc.status = CaseEscalation.Status.RESOLVED
            esc.resolved_at = timezone.now()
            esc.resolved_by = u
            esc.note = (esc.note + "\n" if esc.note else "") + \
                f"Resolved by {u.get_full_name() or u.username}: {request.data.get('note', '')}"
            esc.save()
        return Response(_esc_dict(esc))