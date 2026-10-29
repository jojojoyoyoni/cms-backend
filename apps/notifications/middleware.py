from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs

@database_sync_to_async
def get_user_from_token(token_string):
    # Import inside the function so Django is fully ready
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return None

class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser
        
        scope['user'] = AnonymousUser()
        
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if token:
            user = await get_user_from_token(token)
            if user:
                scope['user'] = user

        return await self.app(scope, receive, send)