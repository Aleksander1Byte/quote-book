from django.test import TestCase
from django.core.exceptions import ValidationError
from parameterized import parameterized
from datetime import date, timedelta
from .models import Quote
from unittest import expectedFailure


class QuoteModelValidationTest(TestCase):
    @parameterized.expand(
        [
            ("valid_data", "Test quote", "Test Author", "user_123", True, None),
            ("empty_text", "", "Author", "user_123", False, "text"),
            ("text_too_long", "x" * 501, "Author", "123", False, "text"),
            ("empty_author", "Text", "", "user_123", False, "author"),
            ("author_too_long", "Text", "A" * 101, "user_123", False, "author"),
            ("empty_user_id", "Text", "Author", "", False, "user_id"),
            ("user_id_too_long", "Text", "Author", "u" * 31, False, "user_id"),
        ]
    )
    def test_quote_validation(
        self, name, text, author, user_id, should_be_valid, expected_error_field
    ):
        quote = Quote(text=text, author=author, user_id=user_id, timestamp=date.today())

        if should_be_valid:
            try:
                quote.full_clean()
                quote.save()
                self.assertIsNotNone(quote.id)
            except ValidationError:
                self.fail(f"Validation failed for valid case: {name}")
        else:
            with self.assertRaises(ValidationError) as context:
                quote.full_clean()
            if expected_error_field:
                self.assertIn(expected_error_field, context.exception.message_dict)

    @expectedFailure
    def test_quote_tomorrow(self):
        quote = Quote(
            text="A",
            author="A",
            user_id="1",
            timestamp=date.today() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as context:
            quote.full_clean()

    def test_timestamp_default(self):
        quote = Quote.objects.create(
            text="Test quote",
            author="Test Author",
            user_id="user_123",
        )
        self.assertEqual(quote.timestamp, date.today())
