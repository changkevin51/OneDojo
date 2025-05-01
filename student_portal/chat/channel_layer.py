#### filepath: student_portal/chat/channel_layer.py
import json
from uuid import uuid4
from asgiref.sync import sync_to_async
from channels.layers import BaseChannelLayer
from .models import Channel, ChannelGroup, ChannelMessage

class SQLiteChannelLayer(BaseChannelLayer): #inheritance

    is_group = True

    def __init__(self, prefix="chan", **kwargs):
        super().__init__(**kwargs)
        self.prefix = prefix

    @sync_to_async
    def new_channel(self, prefix=None):
        name = f"{prefix or self.prefix}-{uuid4().hex}"
        Channel.objects.create(name=name)
        return name

    @sync_to_async
    def send(self, channel, message):
        chan = Channel.objects.get(name=channel)
        ChannelMessage.objects.create(channel=chan, message=json.dumps(message))

    @sync_to_async

    def receive(self, channel):
        try:
            chan = Channel.objects.get(name=channel)
            msg = ChannelMessage.objects.filter(channel=chan).order_by("id").first()
            
            if not msg:
                return {'type': 'no_op'}  # can't return none bruh
            
            try:
                data = json.loads(msg.message)
                

                if 'type' not in data:
                    # print(f"Warning: Message has no 'type' field: {data}")

                    data['type'] = 'chat_message'
                    

                msg.delete()
                return data
                
            except json.JSONDecodeError as e:
                # print(f"Error decoding message: {e}")

                msg.delete()
                return None
                
        except Channel.DoesNotExist:
            # print(f"Channel not found: {channel}")
            return None

    @sync_to_async
    def group_add(self, group, channel):
        chan = Channel.objects.get(name=channel)
        ChannelGroup.objects.get_or_create(group_name=group, channel=chan)

    @sync_to_async
    def group_discard(self, group, channel):
        chan = Channel.objects.get(name=channel)
        ChannelGroup.objects.filter(group_name=group, channel=chan).delete()

    @sync_to_async
    def group_send(self, group, message):
        members = ChannelGroup.objects.filter(group_name=group).select_related("channel")
        payload = json.dumps(message)
        for m in members:
            ChannelMessage.objects.create(channel=m.channel, message=payload)