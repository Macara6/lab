
from django.contrib.auth.backends import ModelBackend
from .models import *





class CaseSensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
