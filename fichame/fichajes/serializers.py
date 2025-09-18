from rest_framework import serializers
from .models import Fichaje
from datetime import datetime, timedelta

class FichajeSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Fichaje
        fields = ["id", "user", "fecha", "hora_inicio", "hora_fin", "duration_minutes"]
        read_only_fields = ["user", "fecha"]

    def get_duration_minutes(self, obj):
        if obj.hora_inicio and obj.hora_fin:
            # Duración robusta (si cruzara medianoche)
            start_dt = datetime.combine(obj.fecha, obj.hora_inicio)
            end_dt = datetime.combine(obj.fecha, obj.hora_fin)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            return max(0, int((end_dt - start_dt).total_seconds() // 60))
        return None

    def validate(self, attrs):
        # Validación simple: fin posterior a inicio (cuando ambos vengan informados)
        hora_inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        hora_fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise serializers.ValidationError("La hora de salida debe ser posterior a la de entrada.")
        return attrs
