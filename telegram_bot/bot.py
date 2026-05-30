import math
import os
from datetime import date, datetime

import requests
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from helpers import (
    KEEP_DATE_BUTTON,
    PAGE_LIMIT,
    TODAY_BUTTON,
    parse_callback,
    parse_date_input,
    validate_author,
    validate_text,
)

load_dotenv()

API_URL = os.getenv("API_URL")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SOCKS5 = os.getenv("SOCKS5", "f").lower() in ("t", "true", "1", "y", "yes")
proxy_url = os.getenv("proxy_url")


class SimpleQuoteBot:
    def __init__(self):
        if SOCKS5:
            self.application = (
                Application.builder()
                .token(BOT_TOKEN)
                .proxy(proxy_url)
                .get_updates_proxy(proxy_url)
                .build()
            )
        else:
            self.application = Application.builder().token(BOT_TOKEN).build()
        self._setup_handlers()
        self.main_keyboard = ReplyKeyboardMarkup(
            [
                ["📖 Мои цитаты", "➕ Добавить цитату"],
                ["🔍 Поиск по автору", "📅 Поиск по дате"],
                ["🗑️ Удалить цитату", "🎲 Случайность"],
            ],
            resize_keyboard=True,
        )
        self.cancel_keyboard = ReplyKeyboardMarkup(
            [["🔙 Отмена"]], resize_keyboard=True
        )
        self.date_keyboard = ReplyKeyboardMarkup(
            [[TODAY_BUTTON], ["🔙 Отмена"]], resize_keyboard=True
        )
        self.edit_date_keyboard = ReplyKeyboardMarkup(
            [[KEEP_DATE_BUTTON, TODAY_BUTTON], ["🔙 Отмена"]], resize_keyboard=True
        )

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("quotes", self.list_quotes))
        self.application.add_handler(CommandHandler("add", self.add_quote))
        self.application.add_handler(CommandHandler("search", self.search_quote))
        self.application.add_handler(CommandHandler("search_date", self.search_by_date))
        self.application.add_handler(CommandHandler("delete", self.delete_quote))
        self.application.add_handler(CommandHandler("random", self.random_quote))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 Бот для управления цитатами\n\n"
            "Используйте кнопки ниже для управления цитатами:",
            reply_markup=self.main_keyboard,
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📖 Доступные команды:\n\n"
            "📖 Мои цитаты — показать все ваши цитаты\n"
            "➕ Добавить цитату — создать новую\n"
            "🎲 Случайность — случайная цитата (с кнопкой «Ещё одну»)\n"
            "🔍 Поиск по автору — без учёта регистра, по части имени\n"
            "📅 Поиск по дате — найти цитаты за дату\n"
            "🗑️ Удалить цитату — кнопка 🗑 рядом с цитатой\n"
            "✏️ Редактировать — кнопка ✏️ рядом с цитатой в списке\n\n"
            "Формат даты: ГГГГ-ММ-ДД (например: 2025-10-24)\n\n"
            "Команды: /quotes /add /random /search /search_date /delete"
        )
        await update.message.reply_text(help_text, reply_markup=self.main_keyboard)

    # ------------------------------------------------------------------ #
    # HTTP
    # ------------------------------------------------------------------ #
    def _make_api_request(self, endpoint, method="GET", params=None, json_data=None):
        """Запрос к API. Возвращает Response (любой код) или None при сбое сети."""
        url = f"{API_URL}{endpoint}"
        try:
            if method == "GET":
                return requests.get(url, params=params, timeout=10)
            if method == "POST":
                return requests.post(url, json=json_data, timeout=10)
            if method == "PATCH":
                return requests.patch(url, json=json_data, params=params, timeout=10)
            if method == "DELETE":
                return requests.delete(url, params=params, timeout=10)
        except requests.exceptions.RequestException:
            return None
        return None

    def _fetch_quotes(self, params):
        """Получить страницу цитат. Возвращает (data|None, error|None).

        error: 'network' — сеть недоступна, 'http' — не-200 ответ.
        """
        response = self._make_api_request("/quotes/", "GET", params=params)
        if response is None:
            return None, "network"
        if response.status_code == 200:
            return response.json(), None
        return None, "http"

    @staticmethod
    def _error_text(error):
        if error == "network":
            return "❌ Сервис недоступен, попробуйте позже"
        return "❌ Не удалось загрузить цитаты"

    @staticmethod
    async def _safe_edit(query, text, markup=None):
        """Редактирование сообщения, устойчивое к 'message is not modified'."""
        try:
            await query.edit_message_text(text, reply_markup=markup)
        except BadRequest:
            pass

    # ------------------------------------------------------------------ #
    # Рендеринг списка цитат
    # ------------------------------------------------------------------ #
    @staticmethod
    def _empty_text(mode, params):
        if params.get("author"):
            return f"🔍 По автору «{params['author']}» ничего не найдено"
        if params.get("timestamp"):
            return f"📅 За {params['timestamp']} цитат не найдено"
        if mode == "delete":
            return "📝 У вас пока нет цитат для удаления"
        return "📝 У вас пока нет цитат.\nДобавьте первую — кнопка ➕ Добавить цитату"

    @staticmethod
    def _format_page(data, params, title):
        quotes = data.get("results", [])
        count = data.get("count", len(quotes))
        offset = int(params.get("offset", 0))

        lines = [title, ""]
        for number, quote in enumerate(quotes, offset + 1):
            line = f'{number}. "{quote["text"]}"\n— {quote["author"]}'
            if quote.get("timestamp"):
                line += f" ({quote['timestamp']})"
            lines.append(line + "\n")

        total_pages = max(1, math.ceil(count / PAGE_LIMIT))
        current_page = offset // PAGE_LIMIT + 1
        lines.append(f"📚 Всего цитат: {count} · стр. {current_page}/{total_pages}")
        return "\n".join(lines)

    @staticmethod
    def _build_markup(quotes, data, offset, mode):
        rows = []
        if mode in ("delete", "edit"):
            icon = "🗑" if mode == "delete" else "✏️"
            action = "del" if mode == "delete" else "edit"
            for number, quote in enumerate(quotes, offset + 1):
                rows.append(
                    [
                        InlineKeyboardButton(
                            f"{icon} {number}",
                            callback_data=f"{action}:{quote['id']}",
                        )
                    ]
                )

        nav = []
        if data.get("previous"):
            nav.append(
                InlineKeyboardButton(
                    "◀️", callback_data=f"nav:{max(0, offset - PAGE_LIMIT)}"
                )
            )
        if data.get("next"):
            nav.append(
                InlineKeyboardButton("▶️", callback_data=f"nav:{offset + PAGE_LIMIT}")
            )
        if nav:
            rows.append(nav)

        return InlineKeyboardMarkup(rows) if rows else None

    async def _send_page(self, update, context, params, title, mode):
        """Отправить новую страницу цитат (из reply-кнопки/команды)."""
        data, error = self._fetch_quotes(params)
        if error:
            await update.message.reply_text(
                self._error_text(error), reply_markup=self.main_keyboard
            )
            return

        quotes = data.get("results", [])
        if not quotes:
            await update.message.reply_text(
                self._empty_text(mode, params), reply_markup=self.main_keyboard
            )
            return

        context.user_data["nav"] = {
            "params": dict(params),
            "title": title,
            "mode": mode,
        }
        text = self._format_page(data, params, title)
        markup = self._build_markup(quotes, data, int(params.get("offset", 0)), mode)
        await update.message.reply_text(text, reply_markup=markup or self.main_keyboard)

    async def _render_into(self, query, context, data, params, title, mode):
        """Перерисовать страницу цитат на месте (из callback)."""
        quotes = data.get("results", [])
        if not quotes:
            context.user_data.pop("nav", None)
            await self._safe_edit(query, self._empty_text(mode, params))
            return

        context.user_data["nav"] = {
            "params": dict(params),
            "title": title,
            "mode": mode,
        }
        text = self._format_page(data, params, title)
        markup = self._build_markup(quotes, data, int(params.get("offset", 0)), mode)
        await self._safe_edit(query, text, markup)

    # ------------------------------------------------------------------ #
    # Команды-обработчики меню
    # ------------------------------------------------------------------ #
    async def list_quotes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = f"{update.effective_user.id}"
        await self._send_page(
            update,
            context,
            {"user_id": user_id, "limit": PAGE_LIMIT, "offset": 0},
            "📖 Ваши цитаты",
            "view",
        )

    async def delete_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = f"{update.effective_user.id}"
        await self._send_page(
            update,
            context,
            {"user_id": user_id, "limit": PAGE_LIMIT, "offset": 0},
            "🗑️ Удаление — нажмите 🗑 у цитаты",
            "delete",
        )

    async def search_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👤 Введите имя автора (можно часть, регистр не важен):",
            reply_markup=self.cancel_keyboard,
        )
        context.user_data["awaiting_search_author"] = True

    async def search_by_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📅 Введите дату ГГГГ-ММ-ДД (например: 2025-10-24):",
            reply_markup=self.date_keyboard,
        )
        context.user_data["awaiting_search_date"] = True

    async def add_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "✍️ Напишите текст цитаты:", reply_markup=self.cancel_keyboard
        )
        context.user_data["awaiting_quote"] = True
        context.user_data["quote_stage"] = "text"

    def _random_payload(self, user_id):
        """Возвращает (text, InlineKeyboardMarkup|None) для случайной цитаты."""
        response = self._make_api_request(f"/random/{user_id}", "GET")
        if response is None:
            return "❌ Сервис недоступен, попробуйте позже", None
        if response.status_code == 200:
            quote = response.json()
            text = f'🎲 Случайная цитата\n\n"{quote["text"]}"\n— {quote["author"]}'
            if quote.get("timestamp"):
                text += f" ({quote['timestamp']})"
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎲 Ещё одну", callback_data="rand")]]
            )
            return text, markup
        return (
            "📝 У вас пока нет цитат.\nДобавьте первую — кнопка ➕ Добавить цитату",
            None,
        )

    async def random_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text, markup = self._random_payload(f"{update.effective_user.id}")
        await update.message.reply_text(text, reply_markup=markup or self.main_keyboard)

    # ------------------------------------------------------------------ #
    # Inline callbacks
    # ------------------------------------------------------------------ #
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        action, value = parse_callback(query.data)
        user_id = f"{query.from_user.id}"

        if action == "nav":
            await self._handle_nav(query, context, int(value))
        elif action == "del":
            await self._handle_delete(query, context, value, user_id)
        elif action == "edit":
            await self._handle_edit_start(query, context, value)
        elif action == "rand":
            text, markup = self._random_payload(user_id)
            await self._safe_edit(query, text, markup)

    async def _handle_nav(self, query, context, offset):
        nav = context.user_data.get("nav")
        if not nav:
            await self._safe_edit(query, "Список устарел. Откройте его заново из меню.")
            return
        params = dict(nav["params"])
        params["offset"] = offset
        data, error = self._fetch_quotes(params)
        if error:
            await self._safe_edit(query, self._error_text(error))
            return
        await self._render_into(query, context, data, params, nav["title"], nav["mode"])

    async def _handle_delete(self, query, context, quote_id, user_id):
        response = self._make_api_request(
            f"/quotes/{quote_id}/", "DELETE", params={"user_id": user_id}
        )
        if response is None or response.status_code not in (200, 204):
            await self._safe_edit(query, "❌ Не удалось удалить цитату")
            return

        nav = context.user_data.get("nav")
        if not nav:
            await self._safe_edit(query, "✅ Цитата удалена")
            return

        params = dict(nav["params"])
        data, error = self._fetch_quotes(params)
        if error:
            await self._safe_edit(query, self._error_text(error))
            return

        # Если страница опустела — шагнём на предыдущую
        if not data.get("results") and int(params.get("offset", 0)) > 0:
            params["offset"] = max(0, int(params.get("offset", 0)) - PAGE_LIMIT)
            data, error = self._fetch_quotes(params)
            if error:
                await self._safe_edit(query, self._error_text(error))
                return

        await self._render_into(query, context, data, params, nav["title"], nav["mode"])

    async def _handle_edit_start(self, query, context, quote_id):
        response = self._make_api_request(f"/quotes/{quote_id}/", "GET")
        if response is None or response.status_code != 200:
            await self._safe_edit(query, "❌ Не удалось открыть цитату")
            return

        quote = response.json()
        context.user_data["awaiting_edit"] = True
        context.user_data["edit_id"] = quote_id
        context.user_data["edit_stage"] = "text"
        await query.message.reply_text(
            f'✏️ Текущий текст:\n"{quote["text"]}"\n\nВведите новый текст цитаты:',
            reply_markup=self.cancel_keyboard,
        )

    # ------------------------------------------------------------------ #
    # Текстовый роутер
    # ------------------------------------------------------------------ #
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text

        menu_actions = {
            "📖 Мои цитаты": self.list_quotes,
            "➕ Добавить цитату": self.add_quote,
            "🔍 Поиск по автору": self.search_quote,
            "🎲 Случайность": self.random_quote,
            "📅 Поиск по дате": self.search_by_date,
            "🗑️ Удалить цитату": self.delete_quote,
        }

        if text in menu_actions:
            await menu_actions[text](update, context)
            return

        if text == "🔙 Отмена":
            for key in list(context.user_data.keys()):
                if (
                    key.startswith("awaiting_")
                    or key.startswith("quote_")
                    or key.startswith("edit_")
                ):
                    del context.user_data[key]
            await update.message.reply_text(
                "❌ Действие отменено", reply_markup=self.main_keyboard
            )
            return

        if context.user_data.get("awaiting_quote"):
            await self._handle_quote_creation(update, context, text)
        elif context.user_data.get("awaiting_edit"):
            await self._handle_quote_edit(update, context, text)
        elif context.user_data.get("awaiting_search_author"):
            await self._handle_author_search(update, context, text)
        elif context.user_data.get("awaiting_search_date"):
            await self._handle_date_search(update, context, text)
        else:
            await update.message.reply_text(
                "Используйте кнопки ниже для управления цитатами 👇",
                reply_markup=self.main_keyboard,
            )

    async def _handle_quote_creation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        stage = context.user_data.get("quote_stage")

        if stage == "text":
            error = validate_text(text)
            if error:
                await update.message.reply_text(
                    error, reply_markup=self.cancel_keyboard
                )
                return
            context.user_data["quote_text"] = text
            context.user_data["quote_stage"] = "author"
            await update.message.reply_text(
                "👤 Теперь укажите автора:", reply_markup=self.cancel_keyboard
            )

        elif stage == "author":
            error = validate_author(text)
            if error:
                await update.message.reply_text(
                    error, reply_markup=self.cancel_keyboard
                )
                return
            context.user_data["quote_author"] = text
            context.user_data["quote_stage"] = "timestamp"
            await update.message.reply_text(
                "📅 Укажите дату ГГГГ-ММ-ДД или нажмите «📅 Сегодня»:",
                reply_markup=self.date_keyboard,
            )

        elif stage == "timestamp":
            timestamp, ok = parse_date_input(text)
            if not ok:
                await update.message.reply_text(
                    "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД или «📅 Сегодня».",
                    reply_markup=self.date_keyboard,
                )
                return

            quote_data = {
                "text": context.user_data["quote_text"],
                "author": context.user_data["quote_author"],
                "user_id": f"{update.effective_user.id}",
            }
            if timestamp:
                quote_data["timestamp"] = timestamp

            response = self._make_api_request("/quotes/", "POST", json_data=quote_data)
            if response is None:
                message = "❌ Сервис недоступен, попробуйте позже"
            elif response.status_code == 201:
                message = "✅ Цитата сохранена!"
            else:
                message = "❌ Не удалось сохранить цитату. Проверьте ввод."
            await update.message.reply_text(message, reply_markup=self.main_keyboard)

            for key in [
                "awaiting_quote",
                "quote_stage",
                "quote_text",
                "quote_author",
            ]:
                context.user_data.pop(key, None)

    async def _handle_quote_edit(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        stage = context.user_data.get("edit_stage")

        if stage == "text":
            error = validate_text(text)
            if error:
                await update.message.reply_text(
                    error, reply_markup=self.cancel_keyboard
                )
                return
            context.user_data["edit_text"] = text
            context.user_data["edit_stage"] = "author"
            await update.message.reply_text(
                "👤 Введите нового автора:", reply_markup=self.cancel_keyboard
            )

        elif stage == "author":
            error = validate_author(text)
            if error:
                await update.message.reply_text(
                    error, reply_markup=self.cancel_keyboard
                )
                return
            context.user_data["edit_author"] = text
            context.user_data["edit_stage"] = "timestamp"
            await update.message.reply_text(
                "📅 Новая дата ГГГГ-ММ-ДД, «📅 Сегодня» или «📅 Оставить как есть»:",
                reply_markup=self.edit_date_keyboard,
            )

        elif stage == "timestamp":
            patch_data = {
                "text": context.user_data["edit_text"],
                "author": context.user_data["edit_author"],
            }
            if text != KEEP_DATE_BUTTON:
                timestamp, ok = parse_date_input(text)
                if not ok:
                    await update.message.reply_text(
                        "❌ Неверный формат даты. ГГГГ-ММ-ДД, «📅 Сегодня» "
                        "или «📅 Оставить как есть».",
                        reply_markup=self.edit_date_keyboard,
                    )
                    return
                patch_data["timestamp"] = timestamp or date.today().isoformat()

            quote_id = context.user_data["edit_id"]
            user_id = f"{update.effective_user.id}"
            response = self._make_api_request(
                f"/quotes/{quote_id}/",
                "PATCH",
                params={"user_id": user_id},
                json_data=patch_data,
            )
            if response is None:
                message = "❌ Сервис недоступен, попробуйте позже"
            elif response.status_code == 200:
                message = "✅ Цитата обновлена!"
            else:
                message = "❌ Не удалось обновить цитату. Проверьте ввод."
            await update.message.reply_text(message, reply_markup=self.main_keyboard)

            for key in [
                "awaiting_edit",
                "edit_stage",
                "edit_id",
                "edit_text",
                "edit_author",
            ]:
                context.user_data.pop(key, None)

    async def _handle_author_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        user_id = f"{update.effective_user.id}"
        context.user_data.pop("awaiting_search_author", None)
        await self._send_page(
            update,
            context,
            {"user_id": user_id, "author": text, "limit": PAGE_LIMIT, "offset": 0},
            f"🔍 Цитаты автора «{text}»",
            "view",
        )

    async def _handle_date_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        if text == TODAY_BUTTON:
            date_str = date.today().isoformat()
        else:
            date_str = text
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД или «📅 Сегодня».",
                    reply_markup=self.date_keyboard,
                )
                return

        user_id = f"{update.effective_user.id}"
        context.user_data.pop("awaiting_search_date", None)
        await self._send_page(
            update,
            context,
            {
                "user_id": user_id,
                "timestamp": date_str,
                "limit": PAGE_LIMIT,
                "offset": 0,
            },
            f"📅 Цитаты за {date_str}",
            "view",
        )


def run_bot():
    bot = SimpleQuoteBot()
    print("Bot is running...")
    bot.application.run_polling()


if __name__ == "__main__":
    run_bot()
