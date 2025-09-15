# fichajes/serializers.py
from rest_framework import serializers
from .models import Fichaje

class FichajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fichaje
        fields = ["id", "user", "fecha", "hora_inicio", "hora_fin"]
        read_only_fields = ["user", "fecha"]

    def validate(self, attrs):
        # Validación simple: fin posterior a inicio (cuando ambos vengan informados)
        hora_inicio = attrs.get("hora_inicio", getattr(self.instance, "hora_inicio", None))
        hora_fin = attrs.get("hora_fin", getattr(self.instance, "hora_fin", None))
        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise serializers.ValidationError("La hora de salida debe ser posterior a la de entrada.")
        return attrs
