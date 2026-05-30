from random import choice

from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Quote
from .serializers import QuoteSerializer


class QuoteFilter(FilterSet):
    author = CharFilter(method="filter_author")

    class Meta:
        model = Quote
        fields = ["user_id", "author", "timestamp"]

    def filter_author(self, queryset, name, value):
        # Регистронезависимый поиск-подстрока по lowercase-копии автора.
        # str.lower() корректно работает с кириллицей, в отличие от
        # SQLite LOWER()/icontains, ограниченных ASCII.
        return queryset.filter(author_lower__contains=value.lower())


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = QuoteFilter
    search_fields = ["user_id", "author", "timestamp"]


class QuoteRandomView(APIView):
    def get(self, request, user_id):
        obj = choice(Quote.objects.filter(user_id=user_id).all() or (0,))
        if obj:
            return Response(QuoteSerializer(obj).data)
        return Response({"error": "No quotes found"}, status=404)
