from rest_framework.permissions import BasePermission

class IsOwnerOrEmpresaOrAdmin(BasePermission):
    """
    - trabajador: solo sus propios fichajes
    - empresa / admin: acceso a todos (PoC). TODO: limitar a empleados de su empresa.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, "role", "trabajador")
        if role in ("admin", "empresa"):
            return True
        return obj.user_id == request.user.id
