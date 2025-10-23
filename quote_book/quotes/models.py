from django.db import models
import datetime


class Quote(models.Model):
    text = models.CharField(max_length=500)
    author = models.CharField(max_length=100)
    user_id = models.CharField(max_length=30)
    timestamp = models.DateField(default=datetime.date.today)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created"]
