from rest_framework import permissions

# Granular Permissions
class Permissions:
    # Organizations
    CAN_MANAGE_ORGS = 'organizations.manage'
    # Users
    CAN_MANAGE_USERS = 'users.manage'
    CAN_CREATE_USER = 'users.create'
    # Cases
    CAN_VIEW_CASES = 'cases.view'
    CAN_CREATE_CASE = 'cases.create'
    CAN_UPDATE_CASE = 'cases.update'
    CAN_DELETE_CASE = 'cases.delete'
    CAN_ASSIGN_CASE = 'cases.assign'
    # Audit & Reports
    CAN_VIEW_AUDITS = 'audits.view'
    CAN_VIEW_REPORTS = 'reports.view'

# Strict Role to Permission Mapping based on your matrix
ROLE_PERMISSIONS = {
    'SUPERADMIN': [
        'organizations.manage',
        'users.manage', 
        'audits.view', 
        'reports.view'
        # NO cases.* permissions! Super Admins don't do day-to-day cases.
    ],
    'ORG_ADMIN': [
        'cases.view', 'cases.create', 'cases.update', 'cases.delete', 'cases.assign',
        'users.manage', 'users.create',
        'audits.view',
        'reports.view'
    ],
    'TEAM_LEADER': [
        'cases.view', 'cases.create', 'cases.update', 'cases.assign',
        # NO delete, NO user management
        'reports.view'
    ],
    'ANALYST': [
        'cases.view', 'cases.create', 'cases.update',
        # NO delete, NO assign, NO user management, NO reports
    ]
}

# Custom DRF Permission Class for ViewSets
class HasRolePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        user_perms = ROLE_PERMISSIONS.get(user.role, [])
        
        # Map DRF actions to granular permissions
        if view.action == 'create':
            return 'cases.create' in user_perms
        elif view.action in ['update', 'partial_update']:
            return 'cases.update' in user_perms
        elif view.action == 'destroy':
            return 'cases.delete' in user_perms
        elif view.action in ['list', 'retrieve']:
            return 'cases.view' in user_perms # MUST have view permission!
        
        return False