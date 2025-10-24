FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static

CMD ["python", "manage.py", "runserver", "127.0.0.1:8000"]
