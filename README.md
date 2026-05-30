# 📖 Quote Book
[![CI](https://github.com/Aleksander1Byte/quote-book/actions/workflows/flake8.yml/badge.svg)](https://github.com/Aleksander1Byte/quote-book/actions/workflows/flake8.yml)
[![Tests](https://github.com/Aleksander1Byte/quote-book/actions/workflows/tests.yml/badge.svg)](https://github.com/Aleksander1Byte/quote-book/actions/workflows/tests.yml)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-ff1709?style=for-the-badge&logo=django&logoColor=white)

Проект реализован как REST API на Django + DRF с отдельным Telegram-ботом, взаимодействующим с backend по HTTP

## Что такое Quote Book?

Quote Book - сервис для хранения пользовательских цитат используя REST API с доступом через Telegram-бота

## ⚙️ Реализованная функциональность

### Backend (Django + DRF)
- REST API для CRUD-операций с пользовательскими данными
- Изоляция данных между пользователями (доступ только к своим записям)
- Поиск по автору без учёта регистра и по части имени, поиск по дате
- Сортировка цитат от новых к старым
- Получение случайной записи
- Валидация входных данных и обработка ошибок
- Unit-тесты для моделей, сериализаторов и эндпоинтов

### Клиент (Telegram Bot)
- Отдельный frontend-клиент, взаимодействующий с backend через HTTP (можно подключить прокси SOCKS5)
- Добавление, редактирование, удаление, поиск и получение данных через API
- Inline-кнопки: пагинация и удаление/редактирование прямо в сообщении (✏️/🗑 у каждой цитаты)
- Случайная цитата с кнопкой «🎲 Ещё одну» для повторного броска
- Удобный ввод даты («📅 Сегодня» / «Оставить как есть») и понятные сообщения об ошибках
- Отсутствие прямого доступа к базе данных (строгое отделение от API)

## 🛠 Технологии

**Backend:**
- Python 3.12
- Django + Django REST Framework
- SQLite (с возможностью замены на PostgreSQL)

**Frontend:**
- Telegram Bot (python-telegram-bot)
- Proxy (SOCKS5)

**Инфраструктура и инструменты:**
- Docker, docker-compose
- Github Actions (CI)
- flake8

## 🚀 Установка и запуск

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

## Как пользоваться ботом?
Найдите бота в Telegram: @thequotebook_bot

## Основные команды:
| Команда  | Описание |
| ------------- | ------------- |
| /start  | Начать работу |
| /quotes  | Показать все ваши цитаты |
| /add  | Добавить новую цитату |
| /random  | Случайная цитата |
| /search  | Поиск по автору |
| /search_date  | Поиск по дате |
| /delete  | Удалить цитату |
| /help  | Помощь |

> Редактирование и удаление выполняются inline-кнопками ✏️/🗑 прямо в списке цитат,
> а навигация по страницам — кнопками ◀️/▶️ в том же сообщении.

Пример использования:
```text
Вы: /add

Бот: ✍️ Напишите текст цитаты:

Вы: Я - часть той силы, что вечно хочет зла и вечно совершает благо

Бот: 👤 Теперь укажите автора:

Вы: Мефистофель

Бот: 📅 Укажите дату ГГГГ-ММ-ДД или нажмите «📅 Сегодня»:

Вы: [📅 Сегодня]

Бот: ✅ Цитата сохранена!

Вы: /random

Бот: 🎲 Случайная цитата
     "Я - часть той силы, что вечно хочет зла и вечно совершает благо"
     — Мефистофель
     [🎲 Ещё одну]
```

## Архитектура проекта
```text
┌─────────────────┐    REST API    ┌──────────────────┐     ┌──────────────┐
│   Telegram Bot  │ ◄────────────► │   Django + DRF   │ ◄─► │   Database   │
│    (Frontend)   │                │    (Backend)     │     │              │
└─────────────────┘                └──────────────────┘     └──────────────┘
```

## Автор
Aleksander1Byte

[GitHub](https://github.com/Aleksander1Byte) • [Telegram](https://t.me/aleksander1byte)
