from random import choice

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Quote
from .serializers import QuoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["user_id", "author", "timestamp"]
    search_fields = ["user_id", "author", "timestamp"]


class QuoteRandomView(APIView):
    def get(self, request, user_id):
        obj = choice(Quote.objects.filter(user_id=user_id).all() or (0,))
        if obj:
            return Response(QuoteSerializer(obj).data)
        return Response({"error": "No quotes found"}, status=404)
