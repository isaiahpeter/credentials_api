"""
URL configuration for documents app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet, CertificateViewSet, 
    JobHistoryViewSet, SkillViewSet
)

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'job-history', JobHistoryViewSet, basename='job-history')
router.register(r'skills', SkillViewSet, basename='skill')

urlpatterns = [
    path('', include(router.urls)),
]
