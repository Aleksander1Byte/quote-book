import os

import requests
from dotenv import load_dotenv
from requests.exceptions import ConnectionError
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

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

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("quotes", self.list_quotes))
        self.application.add_handler(CommandHandler("add", self.add_quote))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📚 Бот для управления цитатами\n\n"
            "Команды:\n"
            "/quotes - мои цитаты\n"
            "/add - добавить цитату\n\n"
            "Или просто пришли текст цитаты"
        )

    async def list_quotes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = f"{update.effective_user.id}"

        try:
            response = requests.get(f"{API_URL}/quotes/?user_id={user_id}")
            if response.status_code == 200:
                quotes = response.json()
                if quotes:
                    text = "\n\n".join(
                        [f"\"{q['text']}\"\n— {q['author']}" for q in quotes[:5]]
                    )
                    await update.message.reply_text(f"📖 Ваши цитаты:\n\n{text}")
                else:
                    await update.message.reply_text("📝 У вас пока нет цитат")
            else:
                await update.message.reply_text("❌ Ошибка при загрузке цитат")
        except (ConnectionError, Exception):
            await update.message.reply_text("❌ Ошибка соединения с API")

    async def add_quote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Напишите текст цитаты:")
        context.user_data["awaiting_quote"] = True

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("awaiting_quote"):
            context.user_data["quote_text"] = update.message.text
            context.user_data["awaiting_quote"] = False
            context.user_data["awaiting_author"] = True
            await update.message.reply_text("Теперь укажите автора:")
        elif context.user_data.get("awaiting_author"):
            author = update.message.text
            text = context.user_data["quote_text"]
            user_id = f"{update.effective_user.id}"

            try:
                response = requests.post(
                    f"{API_URL}/quotes/",
                    json={"text": text, "author": author, "user_id": user_id},
                )

                if response.status_code == 201:
                    await update.message.reply_text("✅ Цитата сохранена!")
                else:
                    await update.message.reply_text("❌ Ошибка при сохранении")
            except Exception:
                await update.message.reply_text("❌ Ошибка соединения")

            context.user_data.clear()
        else:
            await update.message.reply_text(
                "Хотите добавить это как цитату? Используйте /add"
            )


def run_bot():
    bot = SimpleQuoteBot()
    print("Bot is running...")
    bot.application.run_polling()


if __name__ == "__main__":
    run_bot()
