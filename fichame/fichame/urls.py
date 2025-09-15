from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views import UserViewSet
from fichajes.views import FichajeViewSet

def health(_):
    return JsonResponse({"ok": True})

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"fichajes", FichajeViewSet, basename="fichajes")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),

    # Auth JWT
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # API
    path("api/", include(router.urls)),
]
