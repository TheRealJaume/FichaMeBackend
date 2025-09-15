# users/views.py
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """
    - Trabajador: solo ve su propio usuario.
    - Empresa/Admin/Staff: puede listar/ver usuarios.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", None) in ("empresa", "admin"):
            return User.objects.all().order_by("id")
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """Devuelve el usuario autenticado."""
        return Response(self.get_serializer(request.user).data)
