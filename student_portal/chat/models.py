from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class ChatRoom(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    sender  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Channel(models.Model):
    name = models.CharField(max_length=255, unique=True)

class ChannelGroup(models.Model):
    group_name = models.CharField(max_length=255)
    channel    = models.ForeignKey(Channel, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("group_name", "channel")

class ChannelMessage(models.Model):
    channel    = models.ForeignKey(Channel, on_delete=models.CASCADE)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)