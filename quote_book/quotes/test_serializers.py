from django.test import TestCase
from django.utils import timezone
from parameterized import parameterized
from rest_framework.exceptions import ErrorDetail
from datetime import date, timedelta
from .models import Quote
from .serializers import QuoteSerializer


class QuoteSerializerDetailedTest(TestCase):
    @parameterized.expand(
        [
            # text
            ("text_valid", "Нормальный текст цитаты", True),
            ("text_empty", "", False),
            ("text_only_spaces", "   ", False),
            ("text_max_length", "A" * 500, True),
            ("text_exceed_max", "A" * 501, False),
            ("text_with_special_chars", "Текст с «кавычками» и \n переносами!", True),
            # author
            ("author_valid", "Нормальный автор", True),
            ("author_empty", "", False),
            ("author_only_spaces", "   ", False),
            ("author_max_length", "A" * 100, True),
            ("author_exceed_max", "A" * 101, False),
            ("author_with_digits", "Автор 123", True),
            ("author_many_digits", "1234567890", True),
            ("author_many_digits2", "123456789987654321", True),
            # user_id
            ("user_id_valid", "user_12345", True, None),
            ("user_id_with_underscore", "user_id_with_underscore", True),
            ("user_id_with_digits", "12345", True),
            ("user_id_mixed", "user_123_v2", True),
            ("user_id_empty", "", False),
            ("user_id_only_spaces", "   ", False),
            ("user_id_max_length", "u" * 30, True),
            ("user_id_exceed_max", "u" * 31, False),
        ]
    )
    def test_field_validation(self, test_name, field_value, should_be_valid):
        test_data = {
            "text": "Нормальный текст",
            "author": "Нормальный автор",
            "user_id": "normal_user_123",
            "timestamp": "2025-10-23",
        }
        fields = {"text", "author", "user_id"}

        for f in fields:
            if f in test_name:
                test_data[f] = field_value  # Rewrite valid data
                expected_error_field = None if should_be_valid else f
                break

        serializer = QuoteSerializer(data=test_data)
        is_valid = serializer.is_valid()

        self.assertEqual(
            is_valid,
            should_be_valid,
            f"Тест '{test_name}' не прошел: ожидалась валидность {should_be_valid}, "
            f"получена {is_valid}. Ошибки: {serializer.errors}",
        )

        if not should_be_valid and expected_error_field:
            self.assertIn(
                expected_error_field,
                serializer.errors,
                f"Ожидалась ошибка в поле '{expected_error_field}', но получены: {serializer.errors.keys()}",
            )

    @parameterized.expand(
        [
            ("valid_date_iso", "2025-10-23", True),
            ("valid_date_future", date.today() + timedelta(days=1), False),
            ("valid_date_past", "2020-01-01", True),
            ("valid_date_very_past", "1999-10-23", True),
            ("valid_date_extra_past", "0999-10-23", True),
            ("valid_date_ultra_past", "0033-04-03", True),
            ("invalid_date_format", "20-01-2025", False),
            ("invalid_date_string", "not_a_date", False),
            ("empty_date", "", False),
            ("null_date", None, False),
            ("not_a_date", "@", False),
            ("invalid_month", "2025-13-01", False),
            ("invalid_day", "2025-02-30", False),
            ("invalid_day2", "2025-09-31", False),
        ]
    )
    def test_timestamp_validation(self, test_name, timestamp_value, should_be_valid):
        test_data = {
            "text": "Текст цитаты",
            "author": "Автор",
            "user_id": "123456789",
            "timestamp": timestamp_value,
        }

        serializer = QuoteSerializer(data=test_data)
        is_valid = serializer.is_valid()

        self.assertEqual(
            is_valid,
            should_be_valid,
            f"Тест timestamp '{test_name}' не прошел. " f"Ошибки: {serializer.errors}",
        )

    @parameterized.expand(
        [
            ("basic_serialization", "Текст 1", "Автор 1", "user_1", date(2025, 1, 1)),
            (
                "special_chars",
                "Текст с «кавычками»",
                "Автор с àccent",
                "user_2",
                date(2024, 1, 2),
            ),
            ("max_length_fields", "A" * 500, "B" * 100, "C" * 30, date(2024, 1, 3)),
            ("minimal_data", "Текст", "Автор", "user", date(2024, 1, 4)),
        ]
    )
    def test_serialization_output(self, test_name, text, author, user_id, timestamp):
        quote = Quote.objects.create(
            text=text, author=author, user_id=user_id, timestamp=timestamp
        )

        serializer = QuoteSerializer(quote)
        serialized_data = serializer.data

        expected_fields = {"id", "text", "author", "user_id", "timestamp", "created"}
        self.assertEqual(
            set(serialized_data.keys()),
            expected_fields,
            f"Тест '{test_name}': ожидались поля {expected_fields}, "
            f"получены {set(serialized_data.keys())}",
        )

        self.assertEqual(serialized_data["text"], text)
        self.assertEqual(serialized_data["author"], author)
        self.assertEqual(serialized_data["user_id"], user_id)
        self.assertEqual(serialized_data["timestamp"], timestamp.isoformat())
        self.assertIsNotNone(serialized_data["created"])
        self.assertIsNotNone(serialized_data["id"])

    @parameterized.expand(
        [
            (
                "create_with_all_fields",
                {
                    "text": "Новая цитата",
                    "author": "Новый автор",
                    "user_id": "new_user_123",
                    "timestamp": "2025-10-23",
                },
                True,
                "Успешное создание со всеми полями",
            ),
            (
                "create_without_timestamp",
                {"text": "Цитата без даты", "author": "Автор", "user_id": "123123123"},
                True,
                "Должна использоваться дата по умолчанию",
            ),
            (
                "create_minimal",
                {"text": "Минимальная цитата", "author": "Автор", "user_id": "1"},
                True,
                "Минимальный набор полей",
            ),
        ]
    )
    def test_deserialization_create(
        self, test_name, input_data, should_succeed, description
    ):
        initial_count = Quote.objects.count()

        serializer = QuoteSerializer(data=input_data)
        is_valid = serializer.is_valid()

        self.assertEqual(
            is_valid,
            should_succeed,
            f"Тест '{test_name}' не прошел валидацию. " f"Ошибки: {serializer.errors}",
        )

        if should_succeed:
            quote = serializer.save()

            self.assertEqual(Quote.objects.count(), initial_count + 1)

            saved_quote = Quote.objects.get(id=quote.id)
            self.assertEqual(saved_quote.text, input_data["text"])
            self.assertEqual(saved_quote.author, input_data["author"])
            self.assertEqual(saved_quote.user_id, input_data["user_id"])

            if "timestamp" in input_data:
                expected_date = date.fromisoformat(input_data["timestamp"])
                self.assertEqual(saved_quote.timestamp, expected_date)
            else:
                self.assertEqual(saved_quote.timestamp, date.today())

    @parameterized.expand(
        [
            (
                "update_all_fields",
                {
                    "text": "Обновленный текст",
                    "author": "Обновленный автор",
                    "user_id": "updated_user",
                    "timestamp": "2000-06-17",
                },
            ),
            ("partial_update_text", {"text": "Только текст изменен"}),
            ("partial_update_author", {"author": "Только автор изменен"}),
        ]
    )
    def test_serializer_update(self, test_name, update_data):
        original_quote = Quote.objects.create(
            text="Исходный текст",
            author="Исходный автор",
            user_id="1234567890",
            timestamp=date(2024, 1, 1),
        )

        serializer = QuoteSerializer(original_quote, data=update_data, partial=True)
        self.assertTrue(
            serializer.is_valid(),
            f"Тест обновления '{test_name}' не прошел валидацию: {serializer.errors}",
        )

        updated_quote = serializer.save()

        for field, value in update_data.items():
            if field == "timestamp":
                expected_date = date.fromisoformat(value)
                self.assertEqual(
                    getattr(updated_quote, field),
                    expected_date,
                    f"Поле {field} не обновилось корректно",
                )
            else:
                self.assertEqual(
                    getattr(updated_quote, field),
                    value,
                    f"Поле {field} не обновилось корректно",
                )

        self.assertEqual(updated_quote.id, original_quote.id)
