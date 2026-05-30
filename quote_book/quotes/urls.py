from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import QuoteBulkImportView, QuoteRandomView, QuoteViewSet

router = DefaultRouter()
router.register(r"quotes", QuoteViewSet)

urlpatterns = [
    path("quotes/bulk/", QuoteBulkImportView.as_view(), name="quote-bulk-import"),
    path("", include(router.urls)),
    path("random/<str:user_id>", QuoteRandomView.as_view(), name="quote-random"),
]
