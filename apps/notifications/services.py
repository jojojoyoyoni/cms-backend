from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification

def send_notification_to_user(user_id, message, case_id=None):
    # 1. Save to Database (This must never fail)
    Notification.objects.create(
        user_id=user_id,
        message=message,
        case_id=case_id
    )
    
    # 2. Send via WebSocket in real-time
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "send_notification",
                    "message": message,
                    "case_id": case_id,
                }
            )
    except Exception as e:
        # Log the error but don't crash the API
        print(f"WebSocket notification failed: {e}")