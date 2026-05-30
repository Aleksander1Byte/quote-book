import unittest

from parameterized import parameterized

from helpers import (
    MAX_AUTHOR_LEN,
    MAX_TEXT_LEN,
    TODAY_BUTTON,
    parse_callback,
    parse_date_input,
    validate_author,
    validate_quote_input,
    validate_text,
)


class ParseCallbackTest(unittest.TestCase):
    @parameterized.expand(
        [
            ("delete", "del:5", ("del", "5")),
            ("edit", "edit:42", ("edit", "42")),
            ("nav", "nav:10", ("nav", "10")),
            ("rand_no_value", "rand", ("rand", "")),
            ("empty", "", ("", "")),
            ("id_with_colon", "del:1:2", ("del", "1:2")),
        ]
    )
    def test_parse_callback(self, name, data, expected):
        self.assertEqual(parse_callback(data), expected)


class ValidateInputTest(unittest.TestCase):
    def test_valid_text_and_author(self):
        self.assertIsNone(validate_text("A" * MAX_TEXT_LEN))
        self.assertIsNone(validate_author("A" * MAX_AUTHOR_LEN))
        self.assertIsNone(validate_quote_input("ok", "author"))

    def test_text_too_long(self):
        self.assertIsNotNone(validate_text("A" * (MAX_TEXT_LEN + 1)))

    def test_author_too_long(self):
        self.assertIsNotNone(validate_author("A" * (MAX_AUTHOR_LEN + 1)))

    def test_quote_input_reports_first_error(self):
        result = validate_quote_input("A" * (MAX_TEXT_LEN + 1), "ok")
        self.assertIsNotNone(result)
        result = validate_quote_input("ok", "A" * (MAX_AUTHOR_LEN + 1))
        self.assertIsNotNone(result)


class ParseDateInputTest(unittest.TestCase):
    @parameterized.expand(
        [
            ("dot", ".", (None, True)),
            ("today_button", TODAY_BUTTON, (None, True)),
            ("valid_date", "2025-10-24", ("2025-10-24", True)),
            ("wrong_format", "24-10-2025", (None, False)),
            ("invalid_value", "2025-02-30", (None, False)),
            ("garbage", "tomorrow", (None, False)),
        ]
    )
    def test_parse_date_input(self, name, text, expected):
        self.assertEqual(parse_date_input(text), expected)


if __name__ == "__main__":
    unittest.main()
