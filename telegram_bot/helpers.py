"""Чистые хелперы бота без зависимостей от Telegram — удобно тестировать."""

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
