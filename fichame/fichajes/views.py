# fichajes/views.py
from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Fichaje
from .serializers import FichajeSerializer
from rest_framework.exceptions import PermissionDenied

class FichajeViewSet(viewsets.ModelViewSet):
    """
    CRUD de segmentos de fichaje + acciones personalizadas:
      POST /api/fichajes/entrada/  -> abre nuevo segmento (si no hay uno abierto)
      POST /api/fichajes/salida/   -> cierra el último segmento abierto
      GET  /api/fichajes/hoy/      -> segmentos del día actual + open + totales
      GET  /api/fichajes/resumen/?year=YYYY&month=MM -> totales por mes
    """
    serializer_class = FichajeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Fichaje.objects.select_related("user").order_by("-fecha", "-id")
        role = getattr(user, "role", "trabajador")
        if role in ("admin", "empresa") or user.is_staff:
            # (Producción: filtra por compañía aquí)
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Evita reasignar user si no eres admin/empresa/staff
        instance = serializer.instance
        user = self.request.user
        role = getattr(user, "role", "trabajador")
        if user.is_staff or role in ("admin", "empresa"):
            serializer.save()
        else:
            serializer.save(user=instance.user)

    # ------------ ACCIONES PERSONALIZADAS ------------

    @decorators.action(detail=False, methods=["post"], url_path="entrada")
    def entrada(self, request):
        # Si existe un segmento abierto (hora_fin is null), no se puede abrir otro
        abierto = Fichaje.objects.filter(user=request.user, hora_inicio__isnull=False, hora_fin__isnull=True).exists()
        if abierto:
            return response.Response({"detail": "Ya tienes un tramo abierto. Ficha salida antes de iniciar otro."},
                                     status=status.HTTP_400_BAD_REQUEST)
        now_local = timezone.localtime()
        f = Fichaje.objects.create(
            user=request.user,
            fecha=timezone.localdate(),
            hora_inicio=now_local.time()
        )
        return response.Response(self.get_serializer(f).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["post"], url_path="salida")
    def salida(self, request):
        # Cierra el último segmento abierto (independiente del día)
        abierto = Fichaje.objects.filter(user=request.user, hora_inicio__isnull=False, hora_fin__isnull=True).order_by("-fecha", "-id").first()
        if not abierto:
            return response.Response({"detail": "No tienes ningún tramo abierto."},
                                     status=status.HTTP_400_BAD_REQUEST)
        now_local = timezone.localtime()
        abierto.hora_fin = now_local.time()
        # Si cruzó medianoche, lo permitimos y calculamos duración en serializer (sumando 1 día)
        abierto.save()
        return response.Response(self.get_serializer(abierto).data)

    @decorators.action(detail=False, methods=["get"], url_path="hoy")
    def hoy(self, request):
        today = timezone.localdate()
        qs = Fichaje.objects.filter(user=request.user, fecha=today).order_by("hora_inicio", "id")

        # Estado abierto
        abierto = Fichaje.objects.filter(user=request.user, hora_inicio__isnull=False, hora_fin__isnull=True).exists()

        # Totales del día (suma de segmentos cerrados y si hay abierto cuenta hasta ahora)
        total_minutes = 0
        for seg in qs:
            if seg.hora_inicio and seg.hora_fin:
                start_dt = datetime.combine(seg.fecha, seg.hora_inicio)
                end_dt = datetime.combine(seg.fecha, seg.hora_fin)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                total_minutes += max(0, int((end_dt - start_dt).total_seconds() // 60))
        if abierto:
            # si hay uno abierto de HOY, acumulamos tiempo parcial hasta ahora
            seg_abierto = Fichaje.objects.filter(user=request.user, fecha=today, hora_fin__isnull=True).order_by("-id").first()
            if seg_abierto and seg_abierto.hora_inicio:
                start_dt = datetime.combine(seg_abierto.fecha, seg_abierto.hora_inicio)
                now_local = timezone.localtime()
                end_dt = datetime.combine(seg_abierto.fecha, now_local.time())
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                total_minutes += max(0, int((end_dt - start_dt).total_seconds() // 60))

        return response.Response({
            "date": str(today),
            "open": bool(abierto),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2),
            "segments": FichajeSerializer(qs, many=True).data
        })

    @decorators.action(detail=False, methods=["get"], url_path="resumen")
    def resumen(self, request):
        year = int(request.query_params.get("year", timezone.localdate().year))
        month = int(request.query_params.get("month", timezone.localdate().month))
        qs = self.get_queryset().filter(fecha__year=year, fecha__month=month)

        total_minutes = 0
        for f in qs:
            if f.hora_inicio and f.hora_fin:
                start_dt = datetime.combine(f.fecha, f.hora_inicio)
                end_dt = datetime.combine(f.fecha, f.hora_fin)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
                total_minutes += max(0, int((end_dt - start_dt).total_seconds() // 60))

        return response.Response({
            "year": year,
            "month": month,
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2),
            "segments_count": qs.count()
        })

    def perform_destroy(self, instance):
        user = self.request.user
        role = getattr(user, "role", "trabajador")
        # Solo admin/empresa/staff pueden borrar cualquiera; el resto, solo los suyos
        if not (user.is_staff or role in ("admin", "empresa")) and instance.user_id != user.id:
            raise PermissionDenied("No puedes eliminar este registro.")
        instance.delete()