from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import UserViewSet

router_v1 = DefaultRouter()

router_v1.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router_v1.urls)),
]