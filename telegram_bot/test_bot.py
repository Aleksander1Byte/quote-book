import json
import unittest

from parameterized import parameterized

from helpers import (
    MAX_AUTHOR_LEN,
    MAX_TEXT_LEN,
    TODAY_BUTTON,
    build_export_payload,
    parse_callback,
    parse_date_input,
    parse_import_payload,
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


class BuildExportPayloadTest(unittest.TestCase):
    SAMPLE = [
        {
            "id": 2,
            "text": "Вторая",
            "author": "Автор B",
            "user_id": "u1",
            "timestamp": "2025-10-27",
            "created": "2025-10-27T07:00:00Z",
        },
        {
            "id": 1,
            "text": "Первая",
            "author": "Автор A",
            "user_id": "u1",
            "timestamp": "2025-10-24",
            "created": "2025-10-24T09:00:00Z",
        },
    ]

    def test_keeps_only_export_fields(self):
        payload = build_export_payload(self.SAMPLE)
        for record in payload["results"]:
            self.assertEqual(
                set(record.keys()), {"text", "author", "timestamp", "created"}
            )

    def test_count_matches_results(self):
        payload = build_export_payload(self.SAMPLE)
        self.assertEqual(payload["count"], len(payload["results"]))
        self.assertEqual(payload["count"], 2)

    def test_sorted_ascending_by_created(self):
        payload = build_export_payload(self.SAMPLE)
        texts = [r["text"] for r in payload["results"]]
        self.assertEqual(texts, ["Первая", "Вторая"])

    def test_empty_input(self):
        self.assertEqual(build_export_payload([]), {"count": 0, "results": []})


class ParseImportPayloadTest(unittest.TestCase):
    def test_accepts_results_wrapper(self):
        valid, skipped = parse_import_payload(
            {"results": [{"text": "T", "author": "A"}]}
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(valid, [{"text": "T", "author": "A"}])

    def test_accepts_bare_list(self):
        valid, skipped = parse_import_payload([{"text": "T", "author": "A"}])
        self.assertEqual(valid, [{"text": "T", "author": "A"}])
        self.assertEqual(skipped, 0)

    def test_accepts_utf8_bytes(self):
        raw = json.dumps({"results": [{"text": "Цитата", "author": "Автор"}]}).encode(
            "utf-8"
        )
        valid, skipped = parse_import_payload(raw)
        self.assertEqual(valid, [{"text": "Цитата", "author": "Автор"}])

    @parameterized.expand(
        [
            ("malformed_json", b"{not json"),
            ("top_level_int", 42),
            ("top_level_str", "hello"),
            ("dict_without_results", {"foo": 1}),
        ]
    )
    def test_unreadable_returns_none(self, name, raw):
        self.assertEqual(parse_import_payload(raw), (None, 0))

    @parameterized.expand(
        [
            ("missing_author", {"text": "T"}),
            ("missing_text", {"author": "A"}),
            ("empty_text", {"text": "   ", "author": "A"}),
            ("empty_author", {"text": "T", "author": ""}),
            ("text_too_long", {"text": "A" * (MAX_TEXT_LEN + 1), "author": "A"}),
            ("author_too_long", {"text": "T", "author": "A" * (MAX_AUTHOR_LEN + 1)}),
            ("not_a_dict", "just a string"),
        ]
    )
    def test_skips_invalid_records(self, name, item):
        valid, skipped = parse_import_payload([item])
        self.assertEqual(valid, [])
        self.assertEqual(skipped, 1)

    def test_ignores_id_user_id_created(self):
        valid, _ = parse_import_payload(
            [
                {
                    "id": 5,
                    "text": "T",
                    "author": "A",
                    "user_id": "someone_else",
                    "created": "2025-01-01T00:00:00Z",
                }
            ]
        )
        self.assertEqual(valid, [{"text": "T", "author": "A"}])

    def test_bad_timestamp_kept_without_it(self):
        valid, skipped = parse_import_payload(
            [{"text": "T", "author": "A", "timestamp": "27.10.2025"}]
        )
        self.assertEqual(skipped, 0)
        self.assertEqual(valid, [{"text": "T", "author": "A"}])

    def test_good_timestamp_kept(self):
        valid, _ = parse_import_payload(
            [{"text": "T", "author": "A", "timestamp": "2025-10-24"}]
        )
        self.assertEqual(
            valid, [{"text": "T", "author": "A", "timestamp": "2025-10-24"}]
        )

    def test_mixed_skipped_count(self):
        valid, skipped = parse_import_payload(
            [
                {"text": "Good", "author": "A"},
                {"text": "", "author": "A"},
                {"author": "no text"},
                "garbage",
            ]
        )
        self.assertEqual(len(valid), 1)
        self.assertEqual(skipped, 3)

    def test_roundtrip_preserves_order(self):
        sample = BuildExportPayloadTest.SAMPLE
        raw = json.dumps(build_export_payload(sample)).encode("utf-8")
        valid, skipped = parse_import_payload(raw)
        self.assertEqual(skipped, 0)
        self.assertEqual([r["text"] for r in valid], ["Первая", "Вторая"])
        self.assertEqual([r["author"] for r in valid], ["Автор A", "Автор B"])


if __name__ == "__main__":
    unittest.main()
