import datetime

from django.db import models

from .validators import validate_date


class Quote(models.Model):
    text = models.CharField(max_length=500)
    author = models.CharField(max_length=100)
    # Денормализованная lowercase-копия автора для регистронезависимого
    # поиска-подстроки, работающего и на SQLite (включая кириллицу).
    author_lower = models.CharField(
        max_length=100, editable=False, blank=True, default=""
    )
    user_id = models.CharField(max_length=30)
    timestamp = models.DateField(
        default=datetime.date.today, validators=[validate_date]
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        self.author_lower = self.author.lower()
        super().save(*args, **kwargs)
