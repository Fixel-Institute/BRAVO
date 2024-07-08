from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from . import models

def ValidateAuthToken(token):
    try:
        access = AccessToken(token)
    except Exception as e:
        return None

    user = models.PlatformUser.nodes.get_or_none(user_id=access.get("user"))
    if not user:
        return None # User is deleted
    
    user.is_authenticated = True
    return user

class BRAVOJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        if "X-Secure-API-Key" in request.headers:
            secure_key = request.headers["X-Secure-API-Key"]
            key = models.SecureKey.nodes.get_or_none(token_id=secure_key)
            if not key:
                return None
            
            for user in key.associated_user:
                request.csrf_processing_done = True
                user.is_authenticated = True
                user.api_access = True
                return (user, None)
            return None

        try:
            access = AccessToken(request.COOKIES["accessToken"])
        except Exception as e:
            return None

        user = models.PlatformUser.nodes.get_or_none(user_id=access.get("user"))
        if not user:
            return None # User is deleted
        
        user.is_authenticated = True
        return (user, None)

from django.middleware.csrf import CsrfViewMiddleware
class BRAVOCSRFViewMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if "X-Secure-API-Key" in request.headers:
            return None
        return super().process_view(request, callback=callback, callback_args=callback_args, callback_kwargs=callback_kwargs)
        