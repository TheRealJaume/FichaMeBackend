# fichajes/views.py
from datetime import datetime
from django.utils.timezone import now
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Fichaje
from .serializers import FichajeSerializer

class IsAuthenticated(permissions.IsAuthenticated):
    pass

class FichajeViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal de Fichajes con acciones personalizadas:
    - POST /api/fichajes/entrada/  -> fichar entrada (acción)
    - POST /api/fichajes/salida/   -> fichar salida (acción)
    - GET  /api/fichajes/hoy/      -> fichaje de hoy del usuario
    - GET  /api/fichajes/resumen/?mes=MM&anio=YYYY -> total horas del mes
    CRUD:
    - Trabajador: opera sobre sus propios fichajes.
    - Empresa/Admin/Staff: puede listar/ver todos (y crear si lo deseas).
    """
    serializer_class = FichajeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Fichaje.objects.select_related("user").order_by("-fecha", "-id")
        if user.is_staff or getattr(user, "role", None) in ("empresa", "admin"):
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        # Asigna el usuario autenticado por defecto en altas manuales
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Evita reasignar fichajes a otro usuario si no es staff/admin
        instance = serializer.instance
        user = self.request.user
        if not (user.is_staff or getattr(user, "role", None) in ("empresa", "admin")):
            serializer.save(user=instance.user)
        else:
            serializer.save()

    # ---------- ACCIONES PERSONALIZADAS ----------

    @action(detail=False, methods=["post"], url_path="entrada")
    def fichar_entrada(self, request):
        today = now().date()
        fichaje, created = Fichaje.objects.get_or_create(user=request.user, fecha=today)
        if fichaje.hora_inicio:
            return Response({"detail": "Ya has fichado la entrada hoy."}, status=status.HTTP_400_BAD_REQUEST)
        fichaje.hora_inicio = now().time()
        fichaje.save()
        return Response(self.get_serializer(fichaje).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="salida")
    def fichar_salida(self, request):
        today = now().date()
        try:
            fichaje = Fichaje.objects.get(user=request.user, fecha=today)
        except Fichaje.DoesNotExist:
            return Response({"detail": "No hay entrada registrada hoy."}, status=status.HTTP_400_BAD_REQUEST)
        if fichaje.hora_fin:
            return Response({"detail": "Ya has fichado la salida hoy."}, status=status.HTTP_400_BAD_REQUEST)
        fichaje.hora_fin = now().time()
        fichaje.save()
        return Response(self.get_serializer(fichaje).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="hoy")
    def hoy(self, request):
        today = now().date()
        try:
            fichaje = Fichaje.objects.get(user=request.user, fecha=today)
            return Response(self.get_serializer(fichaje).data)
        except Fichaje.DoesNotExist:
            return Response({"detail": "Sin fichaje hoy."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        """Resumen mensual del usuario autenticado (total horas)."""
        mes = int(request.query_params.get("mes", now().month))
        anio = int(request.query_params.get("anio", now().year))
        qs = Fichaje.objects.filter(user=request.user, fecha__year=anio, fecha__month=mes)

        total_segundos = 0
        for f in qs:
            if f.hora_inicio and f.hora_fin:
                dt_ini = datetime.combine(f.fecha, f.hora_inicio)
                dt_fin = datetime.combine(f.fecha, f.hora_fin)
                total_segundos += max(0, int((dt_fin - dt_ini).total_seconds()))

        return Response({
            "anio": anio,
            "mes": mes,
            "total_horas": round(total_segundos / 3600, 2),
            "fichajes": FichajeSerializer(qs, many=True).data
        })
