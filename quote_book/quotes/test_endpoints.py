from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from parameterized import parameterized
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Quote


class QuoteEndpointTest(APITestCase):
    def setUp(self):
        """Подготовка тестовых данных"""
        self.quote1 = Quote.objects.create(
            text="Первая тестовая цитата",
            author="Тестовый Автор 1",
            user_id="test_user_1",
        )
        self.quote2 = Quote.objects.create(
            text="Вторая тестовая цитата",
            author="Тестовый Автор 2",
            user_id="test_user_2",
        )

    @parameterized.expand(
        [
            ("random_by_existing_user", "test_user_1", 200),
            ("random_by_another_user", "test_user_2", 200),
            ("random_by_nonexistent_user", "nonexistent_user", 404),
            ("random_special_chars_user", "@_@", 404),
        ]
    )
    def test_random_endpoint(self, name, user_id, expected_code):
        url = reverse("quote-random", kwargs={"user_id": user_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (
                "list_quotes_success",
                "get",
                reverse("quote-list"),
                None,
                status.HTTP_200_OK,
            ),
            (
                "create_quote_success",
                "post",
                reverse("quote-list"),
                {
                    "text": "Новая цитата через API",
                    "author": "API Автор",
                    "user_id": "api_user_123",
                },
                status.HTTP_201_CREATED,
            ),
            (
                "create_quote_without_text",
                "post",
                reverse("quote-list"),
                {
                    "author": "Только автор",
                    "user_id": "user_123",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "retrieve_quote_success",
                "get",
                reverse("quote-detail", kwargs={"pk": 1}),
                None,
                status.HTTP_200_OK,
            ),
            (
                "retrieve_nonexistent",
                "get",
                reverse("quote-detail", kwargs={"pk": 999}),
                None,
                status.HTTP_404_NOT_FOUND,
            ),
            (
                "update_quote_success",
                "put",
                reverse("quote-detail", kwargs={"pk": 1}),
                {
                    "text": "Обновленный текст",
                    "author": "Обновленный автор",
                    "user_id": "test_user_1",
                },
                status.HTTP_200_OK,
            ),
            (
                "delete_quote_success",
                "delete",
                reverse("quote-detail", kwargs={"pk": 1}),
                None,
                status.HTTP_204_NO_CONTENT,
            ),
        ]
    )
    def test_endpoint_responses(self, name, method, url, data, expected_status):
        if method == "get":
            response = self.client.get(url)
        elif method == "post":
            response = self.client.post(url, data, format="json")
        elif method == "put":
            response = self.client.put(url, data, format="json")
        elif method == "delete":
            response = self.client.delete(url)
        elif method == "patch":
            response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.status_code,
            expected_status,
            f"Тест '{name}' не прошел: ожидался статус {expected_status}, "
            f"получен {response.status_code}."
            f"Ответ: {getattr(response, 'data', 'No data')}",
        )

    @parameterized.expand(
        [
            ("filter_by_existing_user", "test_user_1", 1),
            ("filter_by_another_user", "test_user_2", 1),
            ("filter_by_nonexistent_user", "nonexistent_user", 0),
            ("special_chars_user", "@_@", 0),
        ]
    )
    def test_filter_by_user_id(self, name, user_id, expected_count):
        url = reverse("quote-list")
        response = self.client.get(url, {"user_id": user_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["count"],
            expected_count,
            f"Фильтр по user_id '{user_id}' должен вернуть {expected_count} записей, "
            f"вернул {len(response.data)}",
        )

        if expected_count > 0:
            for quote_data in response.data["results"]:
                self.assertEqual(quote_data["user_id"], user_id)

    @parameterized.expand(
        [
            # author у quote1 (user test_user_1) = "Тестовый Автор 1"
            ("partial_lowercase", "тестовый", 1),
            ("partial_middle", "Автор", 1),
            ("different_case", "ТЕСТОВЫЙ АВТОР 1", 1),
            ("exact_full", "Тестовый Автор 1", 1),
            ("no_match", "Пушкин", 0),
        ]
    )
    def test_filter_by_author_icontains(self, name, author, expected_count):
        """Поиск по автору: без учёта регистра и по части строки (№3)."""
        url = reverse("quote-list")
        response = self.client.get(url, {"user_id": "test_user_1", "author": author})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["count"],
            expected_count,
            f"Поиск автора '{author}' должен вернуть {expected_count} записей",
        )

    def test_ordering_newest_first(self):
        """Список цитат отсортирован от новых к старым по created (№4)."""
        user_id = "ordering_user"
        quote_a = Quote.objects.create(text="A", author="X", user_id=user_id)
        quote_b = Quote.objects.create(text="B", author="X", user_id=user_id)
        quote_c = Quote.objects.create(text="C", author="X", user_id=user_id)

        # Явно задаём distinct created, чтобы порядок был детерминированным
        now = timezone.now()
        Quote.objects.filter(pk=quote_a.pk).update(created=now - timedelta(minutes=2))
        Quote.objects.filter(pk=quote_b.pk).update(created=now - timedelta(minutes=1))
        Quote.objects.filter(pk=quote_c.pk).update(created=now)

        url = reverse("quote-list")
        response = self.client.get(url, {"user_id": user_id, "limit": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        texts = [quote["text"] for quote in response.data["results"]]
        self.assertEqual(texts, ["C", "B", "A"])


class QuoteEndpointRobustnessTest(APITestCase):
    def setUp(self):
        self.url = reverse("quote-list")

    @parameterized.expand(
        [
            # No data
            ("empty_body", "", status.HTTP_400_BAD_REQUEST),
            ("null_body", None, status.HTTP_400_BAD_REQUEST),
            # Broken Json
            ("malformed_json", "{'text': 'test',}", status.HTTP_400_BAD_REQUEST),
            ("unclosed_brace", '{"text": "test"', status.HTTP_400_BAD_REQUEST),
            ("extra_comma", '{"text": "test",}', status.HTTP_400_BAD_REQUEST),
            ("just_string", "hello world", status.HTTP_400_BAD_REQUEST),
            ("just_number", "12345", status.HTTP_400_BAD_REQUEST),
            ("just_brackets", "{}", status.HTTP_400_BAD_REQUEST),
            # Wrong Data
            (
                "text_as_function",
                '{"text": exit, "author": "author", "user_id": "user"}',
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "author_as_array",
                '{"text": "text", "author": ["array"], "user_id": "user"}',
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "user_id_as_object",
                '{"text": "text", "author": "author", "user_id": {"key": "value"}}',
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "timestamp_as_array",
                '{"text": "text", "author": "author",'
                '"user_id": "user", "timestamp": ["2025-10-23"]}',
                status.HTTP_400_BAD_REQUEST,
            ),
            # Too big values
            (
                "text_1000_chars",
                {"text": "A" * 1000, "author": "Author", "user_id": "user_123"},
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "author_200_chars",
                {"text": "Normal text", "author": "A" * 200, "user_id": "user_123"},
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "user_id_100_chars",
                {"text": "Normal text", "author": "Author", "user_id": "U" * 100},
                status.HTTP_400_BAD_REQUEST,
            ),
            # Empty data
            (
                "empty_text",
                {"text": "", "author": "Author", "user_id": "user_123"},
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "spaces_only_text",
                {"text": "   ", "author": "Author", "user_id": "user_123"},
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "empty_author",
                {"text": "Text", "author": "", "user_id": "user_123"},
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "empty_user_id",
                {"text": "Text", "author": "Author", "user_id": ""},
                status.HTTP_400_BAD_REQUEST,
            ),
            # Wrong timestamp format
            (
                "invalid_date_format_1",
                {
                    "text": "Text",
                    "author": "Author",
                    "user_id": "user_123",
                    "timestamp": "2025/10/23",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "invalid_date_format_2",
                {
                    "text": "Text",
                    "author": "Author",
                    "user_id": "user_123",
                    "timestamp": "22-10-2025",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "invalid_date_value",
                {
                    "text": "Text",
                    "author": "Author",
                    "user_id": "user_123",
                    "timestamp": "2025-02-30",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                "far_future_date",
                {
                    "text": "Text",
                    "author": "Author",
                    "user_id": "user_123",
                    "timestamp": "5000-01-01",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
            # Other
            (
                "sql_injection_attempt",
                {
                    "text": "test'; DROP TABLE quotes; --",
                    "author": "hacker228",
                    "user_id": "user_123",
                },
                status.HTTP_201_CREATED,
            ),
            (
                "xss_attempt",
                {
                    "text": "<script>alert('xss')</script>",
                    "author": "<b>Author</b>",
                    "user_id": "user_123",
                },
                status.HTTP_201_CREATED,
            ),
            (
                "emoji_text",
                {"text": "😊 эмодзи 🚀", "author": "😎", "user_id": "user_😊"},
                status.HTTP_201_CREATED,
            ),
            (
                "weird_text",
                {
                    "text": "ሰላምהיי.salve你⍨好⨋Æ𓀀𓀃𓀉𓀪𓀭𓀡𓀮𓀳𓀷𓀺𓀼𓀾𓀒𓁁𓁇𓁉 ༗ ࿄ ࿇ ࿃$⅓ ꧁꧂",
                    "author": "Breaker⚠⏧",
                    "user_id": "1234567890",
                },
                status.HTTP_201_CREATED,
            ),
            (
                "extra_fields",
                {
                    "text": "Normal text",
                    "author": "Normal author",
                    "user_id": "normal_user",
                    "unknown_field": "some value",
                    "another_unknown": 12345,
                },
                status.HTTP_201_CREATED,
            ),
            (
                "nested_objects",
                {
                    "text": {"nested": "value"},
                    "author": "Author",
                    "user_id": "user_123",
                },
                status.HTTP_400_BAD_REQUEST,
            ),
        ]
    )
    def test_post_invalid_data_robustness(self, test_name, data, expected_status):
        try:
            if isinstance(data, dict):
                response = self.client.post(self.url, data, format="json")
            else:
                response = self.client.post(
                    self.url, data=data, content_type="application/json"
                )

            self.assertNotEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

            self.assertEqual(
                response.status_code,
                expected_status,
                f"Тест '{test_name}': ожидался статус {expected_status}, "
                f"получен {response.status_code}."
                "Ответ: {getattr(response, 'data', 'No data')}",
            )

            if response.status_code >= status.HTTP_400_BAD_REQUEST:
                self.assertTrue(
                    hasattr(response, "data"),
                    f"При ошибке должен возвращаться {response.data}",
                )

        except Exception as e:
            self.fail(f"Исключение при обработке '{test_name}': {str(e)}")

    @parameterized.expand(
        [
            (
                "wrong_content_type_form",
                "text=hello&author=test",
                "application/x-www-form-urlencoded",
            ),
            ("wrong_content_type_xml", "<text>hello</text>", "application/xml"),
            ("wrong_content_type_text", "plain text", "text/plain"),
            ("wrong_content_type_html", "<html>test</html>", "text/html"),
        ]
    )
    def test_wrong_content_types(self, test_name, data, content_type):
        try:
            response = self.client.post(self.url, data=data, content_type=content_type)

            self.assertNotEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            self.fail(f"Исключение при Content-Type '{content_type}': {str(e)}")

    @parameterized.expand(
        [
            (
                "huge_json_payload",
                {"text": "A" * 10000, "author": "A" * 1000, "user_id": "A" * 100},
            ),
            (
                "many_nested_levels",
                {
                    "text": {"nested1": {"nested2": {"nested3": "value"}}},
                    "author": "test",
                    "user_id": "test",
                },
            ),
            ("array_instead_of_object", [{"text": "test1"}, {"text": "test2"}]),
        ]
    )
    def test_extreme_cases(self, test_name, data):
        try:
            response = self.client.post(self.url, data, format="json")

            self.assertNotEqual(
                response.status_code,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Тест '{test_name}' вызвал 500 ошибку!",
            )

            self.assertTrue(
                response.status_code
                in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                ]
            )

        except Exception as e:
            self.fail(f"Тест '{test_name}' вызвал исключение: {str(e)}")


class QuoteBulkImportTest(APITestCase):
    def setUp(self):
        self.url = reverse("quote-bulk-import")
        self.user_id = "bulk_user"
        self.records = [
            {"text": "Первая", "author": "Автор A", "timestamp": "2025-10-24"},
            {"text": "Вторая", "author": "Автор B", "timestamp": "2025-10-25"},
            {"text": "Третья", "author": "Автор C", "timestamp": "2025-10-26"},
        ]

    def test_imports_valid_list(self):
        response = self.client.post(
            self.url,
            {"user_id": self.user_id, "results": self.records},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 3)
        self.assertEqual(response.data["skipped"], 0)
        self.assertEqual(Quote.objects.filter(user_id=self.user_id).count(), 3)

    def test_accepts_bare_list_body(self):
        items = [dict(r, user_id="ignored") for r in self.records]
        response = self.client.post(self.url, items, format="json")
        # Голый список без top-level user_id → нет user_id → 400.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mixed_valid_and_invalid(self):
        future = (timezone.now().date() + timedelta(days=365)).isoformat()
        records = [
            {"text": "Ок", "author": "A", "timestamp": "2025-10-24"},
            {"text": "A" * 1000, "author": "A"},  # слишком длинный текст
            {"text": "Будущее", "author": "A", "timestamp": future},  # дата в будущем
        ]
        response = self.client.post(
            self.url, {"user_id": self.user_id, "results": records}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["skipped"], 2)
        self.assertEqual(Quote.objects.filter(user_id=self.user_id).count(), 1)

    def test_duplicate_reimport_skips(self):
        body = {"user_id": self.user_id, "results": self.records}
        first = self.client.post(self.url, body, format="json")
        second = self.client.post(self.url, body, format="json")
        self.assertEqual(first.data["created"], 3)
        self.assertEqual(second.data["created"], 0)
        self.assertEqual(second.data["skipped"], 3)
        self.assertEqual(Quote.objects.filter(user_id=self.user_id).count(), 3)

    @parameterized.expand(
        [
            ("missing_user_id", {"results": []}),
            ("results_not_a_list", {"user_id": "u", "results": "nope"}),
            ("empty_user_id", {"user_id": "", "results": []}),
        ]
    )
    def test_bad_request_bodies(self, name, body):
        response = self.client.post(self.url, body, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_per_item_user_id_ignored(self):
        records = [
            {
                "text": "T",
                "author": "A",
                "user_id": "attacker",
                "timestamp": "2025-10-24",
            }
        ]
        self.client.post(
            self.url, {"user_id": self.user_id, "results": records}, format="json"
        )
        self.assertEqual(Quote.objects.filter(user_id="attacker").count(), 0)
        self.assertEqual(Quote.objects.filter(user_id=self.user_id).count(), 1)

    @parameterized.expand(
        [
            ("scalar_int", 42),
            ("scalar_string", "hello"),
            ("scalar_null", None),
        ]
    )
    def test_scalar_body_no_500(self, name, body):
        response = self.client.post(self.url, body, format="json")
        self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
