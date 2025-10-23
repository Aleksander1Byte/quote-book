from django.db import models
import datetime
from .validators import validate_date


class Quote(models.Model):
    text = models.CharField(max_length=500)
    author = models.CharField(max_length=100)
    user_id = models.CharField(max_length=30)
    timestamp = models.DateField(
        default=datetime.date.today, validators=[validate_date]
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
