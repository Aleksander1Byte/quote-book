# 📖 Quote Book - Запомни, а то забудешь
[![CI](https://github.com/Aleksander1Byte/quote-book/actions/workflows/flake8.yml/badge.svg)](https://github.com/Aleksander1Byte/quote-book/actions/workflows/flake8.yml)
[![Tests](https://github.com/Aleksander1Byte/quote-book/actions/workflows/tests.yml/badge.svg)](https://github.com/Aleksander1Byte/quote-book/actions/workflows/tests.yml)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white)

*Сохраняйте вдохновение, пересылайте любимые фразы, находите смысл в словах* ✨

## 🤔 Что такое Quote Book?

Quote Book - это ваш персональный сборник цитат! 📚

**Услышали мудрую мысль? Прочитали вдохновляющую фразу? Хотите сохранить интересное высказывание?**

Теперь у вас есть собственный цифровой дневник для всех важных слов! 💫

## 🌟 Основные возможности

### 🤖 Telegram Bot
- **📝 Добавляйте цитаты** - сохраняйте с автором и датой
- **🎲 Получайте случайные цитаты** - вдохновляйтесь неожиданно!
- **🔒 Полная приватность** - ваши цитаты видны только вам

### 🚀 Backend API
- **⚡ REST API** - Django REST Framework
- **🎯 Случайный выбор** - возможность случайного выбора цитат
- **🔐 Безопасность** - каждый пользователь имеет доступ только к своим данным

## 🛠 Технологии

**Backend:**
- 🐍 Python 3.12
- ⚡ Django + Django REST Framework
- 🗄️ SQLite

**Frontend:**
- 🤖 Telegram Bot (python-telegram-bot)
- 📶 Proxy (SOCKS5)

## 📦 Установка и запуск

### Переменные окружения
Настройте собственный файл .env в соответствии с примером [.env.example](.env.example)

### Backend (Django + DRF)

Клонируем проект
```bash
git clone https://github.com/Aleksander1Byte/quote-book.git
cd quote_book
```
Настраиваем виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```
Устанавливаем зависимости
```bash
pip install -r requirements.txt
```
Проводим миграции и проверяем тесты
```bash
python manage.py migrate
python manage.py test
```
Запуск
```bash
python manage.py runserver
```

### Telegram Bot
```bash
cd telegram_bot
```
Устанавливаем зависимости
```bash
pip install -r requirements-tg.txt
```

Запуск бота
```bash
python bot.py
```

## 🤖 Как пользоваться ботом?
Найдите нашего бота в Telegram: @thequotebook_bot 🔍

## Основные команды:
| Команда  | Описание |
| ------------- | ------------- |
| /start  | 🎯 Начать работу |
| /quotes  | 📖 Показать все ваши цитаты |
| /add  | 📝 Добавить новую цитату |
| /random  | 🎲 Случайная цитата |
| /search  | 🔍 Поиск по автору |
| /search_date  | 📅 Поиск по дате |
| /delete  | 🗑️ Удалить цитату |
| /help  | ❓ Помощь |

Пример использования:
```text
Вы: /add

Бот: ✍️ Напишите текст цитаты:

Вы: Я - часть той силы, что вечно хочет зла и вечно совершает благо

Бот: 👤 Теперь укажите автора:

Вы: Мефистофель

Бот: 📅 Укажите дату в формате ГГГГ-ММ-ДД (или отправьте '.' для текущей даты):

Вы: .

Бот: ✅ Цитата сохранена!

Вы: /random

Бот: 🎲 Случайная цитата
     "Я - часть той силы, что вечно хочет зла и вечно совершает благо"
     — Мефистофель
```

## 🏗 Архитектура проекта
```text
┌─────────────────┐    REST API    ┌──────────────────┐     ┌──────────────┐
│   Telegram Bot  │ ◄────────────► │   Django + DRF   │ ◄─► │   Database   │
│   (Frontend)    │                │    (Backend)     │     │              │
└─────────────────┘                └──────────────────┘     └──────────────┘
```
## 💡 Для кого этот проект?
📚 Читатели - сохраняйте понравившиеся цитаты из книг

🎓 Студенты - собирайте мудрые (или весёлые) мысли преподавателей

💼 Профессионалы - сохраняйте вдохновляющие бизнес-идеи

🧘 Все, кто ценит мудрость - создавайте свою коллекцию вдохновения

## 👨‍💻 Автор
Aleksander1Byte

[GitHub](https://github.com/Aleksander1Byte) • [Telegram](https://t.me/aleksander1byte)

⭐ Если проект вам понравился, не забудьте поставить звездочку!
