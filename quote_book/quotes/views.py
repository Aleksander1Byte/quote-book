from datetime import date
from random import choice

from django.db import transaction
from django_filters.rest_framework import CharFilter, DjangoFilterBackend, FilterSet
from rest_framework import filters, status, viewsets
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


class QuoteBulkImportView(APIView):
    """Массовый импорт цитат одного пользователя.

    Тело: {"user_id": "...", "results": [ {text, author, timestamp?}, ... ]}
    (или голый список вместо объекта). user_id берётся из тела, а не из
    элементов — нельзя записать в чужой сборник. Точные дубли
    (user_id, text, author, timestamp) пропускаются → импорт идемпотентен.
    """

    def post(self, request):
        data = request.data
        if isinstance(data, list):
            user_id, items = None, data
        elif isinstance(data, dict):
            user_id, items = data.get("user_id"), data.get("results")
        else:
            user_id, items = None, None

        if not user_id or not isinstance(items, list):
            return Response(
                {"error": "user_id and results list required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = skipped = 0
        errors = []
        with transaction.atomic():
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    skipped += 1
                    continue
                data = {
                    "text": item.get("text"),
                    "author": item.get("author"),
                    "user_id": user_id,
                }
                if item.get("timestamp"):
                    data["timestamp"] = item["timestamp"]

                effective_ts = data.get("timestamp") or date.today().isoformat()
                if Quote.objects.filter(
                    user_id=user_id,
                    text=data["text"],
                    author=data["author"],
                    timestamp=effective_ts,
                ).exists():
                    skipped += 1
                    continue

                serializer = QuoteSerializer(data=data)
                if serializer.is_valid():
                    serializer.save()
                    created += 1
                else:
                    skipped += 1
                    errors.append({"index": index, "errors": serializer.errors})

        return Response(
            {"created": created, "skipped": skipped, "errors": errors},
            status=status.HTTP_201_CREATED,
        )
