import os
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv
from requests.exceptions import ConnectionError
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

API_URL = os.getenv("API_URL")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SOCKS5 = os.getenv("SOCKS5", "f").lower() in ("t", "true", "1", "y", "yes")
proxy_url = os.getenv("proxy_url")
PAGE_LIMIT = 5


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

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("quotes", self.list_quotes))
        self.application.add_handler(CommandHandler("add", self.add_quote))
        self.application.add_handler(CommandHandler("search", self.search_quote))
        self.application.add_handler(CommandHandler("search_date", self.search_by_date))
        self.application.add_handler(CommandHandler("delete", self.delete_quote))
        self.application.add_handler(CommandHandler("random", self.random_quote))
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
            "📖 Мои цитаты - показать все ваши цитаты\n"
            "➕ Добавить цитату - создать новую цитату\n"
            "🎲 Случайная цитата - получить случайную цитату\n"
            "🔍 Поиск по автору - найти цитаты по автору\n"
            "📅 Поиск по дате - найти цитаты по дате\n"
            "🗑️ Удалить цитату - удалить выбранную цитату\n\n"
            "Формат даты: YYYY-MM-DD (например: 2025-10-24)\n\n"
            "Или используйте команды:\n"
            "/quotes - мои цитаты\n"
            "/add - добавить цитату\n"
            "/random - случайная цитата\n"
            "/search - поиск по автору\n"
            "/search_date - поиск по дате\n"
            "/delete - удалить цитату"
        )
        await update.message.reply_text(help_text, reply_markup=self.main_keyboard)

    def _make_api_request(self, endpoint, method="GET", params=None, json_data=None):
        """Универсальный метод для API запросов"""
        try:
            if method.upper() == "GET":
                response = requests.get(f"{API_URL}{endpoint}", params=params)
            elif method.upper() == "POST":
                response = requests.post(f"{API_URL}{endpoint}", json=json_data)
            elif method.upper() == "DELETE":
                response = requests.delete(f"{API_URL}{endpoint}", params=params)

            if response.status_code in [200, 201, 204]:
                return response
            return None
        except (ConnectionError, Exception):
            return None

    def _get_current_offset(self, response_data):
        """Вычисляет текущий offset из response_data"""
        # Пробуем извлечь offset из current URL
        if "current_params" in response_data:
            return response_data["current_params"].get("offset", 0)

        # Если нет current_params, вычисляем из next/previous
        next_url = response_data.get("next")
        previous_url = response_data.get("previous")

        if next_url:
            parsed = urlparse(next_url)
            params = parse_qs(parsed.query)
            offset = int(params.get("offset", 0)[0])
            return max(0, offset - PAGE_LIMIT)
        elif previous_url:
            parsed = urlparse(previous_url)
            params = parse_qs(parsed.query)
            offset = int(params.get("offset", 0)[0])
            return offset + PAGE_LIMIT
        else:
            return 0

    async def _send_quote_page(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        response_data,
        title="📖 Ваши цитаты",
    ):
        """Отправка страницы с цитатами"""
        quotes = response_data.get("results", [])

        if not quotes:
            await update.message.reply_text(
                "📝 Цитаты не найдены", reply_markup=self.main_keyboard
            )
            return

        current_offset = self._get_current_offset(response_data)
        start_number = current_offset + 1

        text = f"{title}\n\n"
        for i, quote in enumerate(quotes, start_number):
            text += f'{i}. "{quote["text"]}"\n— {quote["author"]}'
            if "timestamp" in quote:
                text += f" ({quote['timestamp']})"
            text += "\n\n"

        count = response_data.get("count", len(quotes))
        text += f"Всего цитат: {count}"

        keyboard = []
        nav_buttons = []

        if response_data.get("previous"):
            nav_buttons.append("◀️ Назад")
        if response_data.get("next"):
            nav_buttons.append("Вперед ▶️")

        if nav_buttons:
            keyboard.append(nav_buttons)
        keyboard.append(["🔙 Главное меню"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(text, reply_markup=reply_markup)

        context.user_data["current_response"] = response_data
        context.user_data["page_title"] = title

    async def _fetch_quotes_page(self, params, title="📖 Ваши цитаты"):
        """Универсальный метод получения страницы цитат"""
        response = self._make_api_request("/quotes/", "GET", params=params)
        if response and response.status_code == 200:
            response_data = response.json()
            response_data["current_params"] = params
            return response_data, title
        return None, title

    async def list_quotes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать цитаты пользователя с пагинацией"""
        user_id = f"{update.effective_user.id}"

        response_data, title = await self._fetch_quotes_page(
            {"user_id": user_id, "limit": PAGE_LIMIT},
        )

        if response_data:
            await self._send_quote_page(update, context, response_data, title)
        else:
            await update.message.reply_text(
                "❌ Ошибка при загрузке цитат", reply_markup=self.main_keyboard
            )

    async def search_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск цитат по автору"""
        await update.message.reply_text(
            "👤 Введите имя автора для поиска:",
            reply_markup=ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True),
        )
        context.user_data["awaiting_search_author"] = True

    async def search_by_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск цитат по дате"""
        await update.message.reply_text(
            "📅 Введите дату в формате ГГГГ-ММ-ДД (например: 2025-10-24):",
            reply_markup=ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True),
        )
        context.user_data["awaiting_search_date"] = True

    async def add_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление цитаты"""
        await update.message.reply_text(
            "✍️ Напишите текст цитаты:",
            reply_markup=ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True),
        )
        context.user_data["awaiting_quote"] = True
        context.user_data["quote_stage"] = "text"

    async def random_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение случайной цитаты"""
        user_id = f"{update.effective_user.id}"
        try:
            response = requests.get(f"{API_URL}/random/{user_id}")
        except Exception:
            response = None

        if response is not None and response.status_code == 200:
            data = response.json()
            text = f'🎲 Случайная цитата\n\n"{data["text"]}"\n— {data["author"]}'
            if "timestamp" in data:
                text += f" ({data['timestamp']})"

            await update.message.reply_text(text, reply_markup=self.main_keyboard)
        elif response is not None and response.status_code == 404:
            await update.message.reply_text(
                "📝 У вас пока нет цитат",
                reply_markup=self.main_keyboard,
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при загрузке цитат", reply_markup=self.main_keyboard
            )

    async def delete_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Удаление цитаты"""
        user_id = f"{update.effective_user.id}"

        response_data, _ = await self._fetch_quotes_page(
            {"user_id": user_id, "limit": 50}
        )

        if response_data:
            quotes = response_data.get("results", [])
            if quotes:
                # Сохраняем ID цитат для удаления
                quote_ids = {str(i + 1): quote["id"] for i, quote in enumerate(quotes)}
                context.user_data["quote_ids"] = quote_ids
                context.user_data["awaiting_delete_choice"] = True

                await self._send_quote_page(
                    update,
                    context,
                    response_data,
                    title="🗑️ Выберите цитату для удаления:",
                )
            else:
                await update.message.reply_text(
                    "📝 У вас пока нет цитат для удаления",
                    reply_markup=self.main_keyboard,
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка при загрузке цитат", reply_markup=self.main_keyboard
            )

    async def _handle_pagination(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, direction
    ):
        """Обработка пагинации"""
        response_data = context.user_data.get("current_response", {})
        url = (
            response_data.get("previous")
            if direction == "back"
            else response_data.get("next")
        )

        if url:
            response = requests.get(url)
            if response.status_code == 200:
                new_response_data = response.json()
                # Сохраняем параметры из URL для вычисления offset
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                current_params = {k: v[0] for k, v in params.items() if k != "offset"}
                current_params["offset"] = int(params.get("offset", [0])[0])
                new_response_data["current_params"] = current_params

                await self._send_quote_page(
                    update,
                    context,
                    new_response_data,
                    title=context.user_data.get("page_title", "📖 Ваши цитаты"),
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при загрузке страницы", reply_markup=self.main_keyboard
                )
        else:
            await update.message.reply_text(
                (
                    "📄 Это последняя страница"
                    if direction == "next"
                    else "📄 Это первая страница"
                ),
                reply_markup=self.main_keyboard,
            )

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

        if text == "◀️ Назад":
            await self._handle_pagination(update, context, "back")
            return

        elif text == "Вперед ▶️":
            await self._handle_pagination(update, context, "next")
            return

        elif text == "🔙 Главное меню":
            # Чистим навигацию
            if "current_response" in context.user_data:
                del context.user_data["current_response"]
            await update.message.reply_text(
                "Главное меню:", reply_markup=self.main_keyboard
            )
            return

        elif text == "🔙 Отмена":
            # Чистим ввод
            for key in list(context.user_data.keys()):
                if key.startswith("awaiting_") or key.startswith("quote_"):
                    del context.user_data[key]
            await update.message.reply_text(
                "❌ Действие отменено", reply_markup=self.main_keyboard
            )
            return

        if context.user_data.get("awaiting_quote"):
            await self._handle_quote_creation(update, context, text)

        elif context.user_data.get("awaiting_search_author"):
            await self._handle_author_search(update, context, text)

        elif context.user_data.get("awaiting_search_date"):
            await self._handle_date_search(update, context, text)

        elif context.user_data.get("awaiting_delete_choice"):
            await self._handle_delete_choice(update, context, text)

        else:
            await update.message.reply_text(
                "Используйте кнопки ниже для управления цитатами 👇",
                reply_markup=self.main_keyboard,
            )

    async def _handle_quote_creation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        """Обработка создания цитаты"""
        if context.user_data.get("quote_stage") == "text":
            context.user_data["quote_text"] = text
            context.user_data["quote_stage"] = "author"
            await update.message.reply_text("👤 Теперь укажите автора:")

        elif context.user_data.get("quote_stage") == "author":
            context.user_data["quote_author"] = text
            context.user_data["quote_stage"] = "timestamp"
            await update.message.reply_text(
                "📅 Укажите дату в формате ГГГГ-ММ-ДД "
                "(или отправьте '.' для текущей даты):"
            )

        elif context.user_data.get("quote_stage") == "timestamp":
            user_id = f"{update.effective_user.id}"
            quote_data = {
                "text": context.user_data["quote_text"],
                "author": context.user_data["quote_author"],
                "user_id": user_id,
            }

            if text != ".":
                try:
                    datetime.strptime(text, "%Y-%m-%d")
                    quote_data["timestamp"] = text
                except ValueError:
                    await update.message.reply_text(
                        "❌ Неверный формат даты. Используйте "
                        "ГГГГ-ММ-ДД или '.' для текущей даты:"
                    )
                    return

            response = self._make_api_request("/quotes/", "POST", json_data=quote_data)

            if response:
                await update.message.reply_text(
                    "✅ Цитата сохранена!", reply_markup=self.main_keyboard
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при сохранении цитаты (проверьте ввод)",
                    reply_markup=self.main_keyboard,
                )

            # Очищаем состояния
            for key in ["awaiting_quote", "quote_stage", "quote_text", "quote_author"]:
                context.user_data.pop(key, None)

    async def _handle_author_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        """Обработка поиска по автору"""
        author = text
        user_id = f"{update.effective_user.id}"

        response_data, title = await self._fetch_quotes_page(
            {"user_id": user_id, "author": author, "limit": PAGE_LIMIT},
            f"🔍 Цитаты автора '{author}':",
        )

        if response_data:
            await self._send_quote_page(update, context, response_data, title)
        else:
            await update.message.reply_text(
                "❌ Ошибка при поиске цитат", reply_markup=self.main_keyboard
            )

        context.user_data.pop("awaiting_search_author", None)

    async def _handle_date_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        """Обработка поиска по дате"""
        date_str = text
        user_id = f"{update.effective_user.id}"

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД:",
                reply_markup=ReplyKeyboardMarkup([["🔙 Отмена"]], resize_keyboard=True),
            )
            return

        response_data, title = await self._fetch_quotes_page(
            {"user_id": user_id, "timestamp": date_str, "limit": PAGE_LIMIT},
            f"📅 Цитаты за {date_str}:",
        )

        if response_data:
            await self._send_quote_page(update, context, response_data, title)
        else:
            await update.message.reply_text(
                "❌ Ошибка при поиске цитат", reply_markup=self.main_keyboard
            )

        context.user_data.pop("awaiting_search_date", None)

    async def _handle_delete_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
    ):
        """Обработка выбора цитаты для удаления"""
        quote_ids = context.user_data.get("quote_ids", {})

        if text in quote_ids:
            quote_id = quote_ids[text]
            user_id = f"{update.effective_user.id}"

            response = self._make_api_request(
                f"/quotes/{quote_id}/", "DELETE", params={"user_id": user_id}
            )

            if response:
                await update.message.reply_text(
                    "✅ Цитата успешно удалена!", reply_markup=self.main_keyboard
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при удалении цитаты", reply_markup=self.main_keyboard
                )
        else:
            await update.message.reply_text(
                "❌ Неверный номер цитаты", reply_markup=self.main_keyboard
            )

        # Очищаем состояние удаления
        context.user_data.pop("awaiting_delete_choice", None)
        context.user_data.pop("quote_ids", None)


def run_bot():
    bot = SimpleQuoteBot()
    print("Bot is running...")
    bot.application.run_polling()


if __name__ == "__main__":
    run_bot()
