from django.conf import settings


def session_timeout(request):
    return {'SESSION_TIMEOUT': settings.SESSION_COOKIE_AGE}
