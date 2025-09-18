# users/views.py
from rest_framework import viewsets, permissions, mixins, decorators, response, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import User
from .serializers import UserSerializer, RegisterSerializer

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  viewsets.GenericViewSet):

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

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="register")
    def register(self, request):
        ser = RegisterSerializer(data=request.data)
        if ser.is_valid():
            user = ser.save()
            return response.Response({"id": user.id, "username": user.username, "email": user.email}, status=status.HTTP_201_CREATED)
        return response.Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

