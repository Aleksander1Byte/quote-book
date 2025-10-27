from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import QuoteRandomView, QuoteViewSet

router = DefaultRouter()
router.register(r"quotes", QuoteViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("random/<str:user_id>", QuoteRandomView.as_view(), name="quote-random"),
]
