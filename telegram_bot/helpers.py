"""Чистые хелперы бота без зависимостей от Telegram — удобно тестировать."""

import json
from datetime import datetime

PAGE_LIMIT = 5
MAX_TEXT_LEN = 500
MAX_AUTHOR_LEN = 100
TODAY_BUTTON = "📅 Сегодня"
KEEP_DATE_BUTTON = "📅 Оставить как есть"


def parse_callback(data):
    """Разбирает callback_data вида 'action:value' → (action, value)."""
    action, _, value = (data or "").partition(":")
    return action, value


def validate_text(text):
    """Возвращает текст ошибки, если текст цитаты слишком длинный, иначе None."""
    if len(text) > MAX_TEXT_LEN:
        return (
            f"❌ Цитата слишком длинная: {len(text)}/{MAX_TEXT_LEN} символов. "
            "Сократите."
        )
    return None


def validate_author(author):
    """Возвращает текст ошибки, если имя автора слишком длинное, иначе None."""
    if len(author) > MAX_AUTHOR_LEN:
        return (
            f"❌ Имя автора слишком длинное: {len(author)}/{MAX_AUTHOR_LEN} символов."
        )
    return None


def validate_quote_input(text, author):
    """Общая валидация ввода цитаты. Возвращает текст ошибки или None."""
    return validate_text(text) or validate_author(author)


def parse_date_input(text):
    """Разбор даты от пользователя.

    Возвращает (value, ok). value: ISO-дата или None (использовать default-сегодня).
    """
    if text in (".", TODAY_BUTTON):
        return None, True
    try:
        datetime.strptime(text, "%Y-%m-%d")
        return text, True
    except ValueError:
        return None, False


def build_export_payload(quotes):
    """Готовит цитаты к выгрузке в JSON.

    quotes: список словарей из API. Возвращает {"count": N, "results": [...]},
    где в каждой записи только text/author/timestamp/created. Отбрасывает
    id, user_id, next, previous. Сортировка по возрастанию created (затем
    timestamp), чтобы при ре-импорте сохранялся исходный порядок.
    """
    cleaned = [
        {
            "text": q.get("text", ""),
            "author": q.get("author", ""),
            "timestamp": q.get("timestamp"),
            "created": q.get("created"),
        }
        for q in quotes
    ]
    cleaned.sort(key=lambda q: (q.get("created") or "", q.get("timestamp") or ""))
    return {"count": len(cleaned), "results": cleaned}


def parse_import_payload(raw):
    """Разбирает загруженный пользователем JSON с цитатами.

    raw: bytes/str (JSON) либо уже распарсенный list/dict.
    Возвращает (valid, skipped):
      valid is None — JSON не читается или верхний уровень не dict/list.
      valid — список записей {"text", "author", "timestamp"?}, отсортированный
              по возрастанию; берётся только text/author/timestamp, поля
              id/user_id/created игнорируются.
      skipped — сколько записей отброшено локально (битый формат/длина).
    Принимает обе формы: {"results": [...]} и голый [...].
    """
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None, 0
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return None, 0

    if isinstance(raw, dict):
        items = raw.get("results")
    elif isinstance(raw, list):
        items = raw
    else:
        items = None
    if not isinstance(items, list):
        return None, 0

    valid = []
    skipped = 0
    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        text, author = item.get("text"), item.get("author")
        if not isinstance(text, str) or not isinstance(author, str):
            skipped += 1
            continue
        text, author = text.strip(), author.strip()
        if not text or not author:
            skipped += 1
            continue
        if validate_text(text) or validate_author(author):  # превышение лимита длины
            skipped += 1
            continue

        record = {"text": text, "author": author}
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            value, ok = parse_date_input(timestamp)
            if ok and value:
                record["timestamp"] = value
            # битая дата — берём запись без timestamp (сервер проставит сегодня)
        record["_created"] = item.get("created") or ""  # только для сортировки
        valid.append(record)

    valid.sort(key=lambda r: (r.get("_created", ""), r.get("timestamp", "")))
    for record in valid:
        record.pop("_created", None)
    return valid, skipped
