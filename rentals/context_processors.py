from django.conf import settings

from .models import UserThemePreference


def session_timeout(request):
    return {'SESSION_TIMEOUT': settings.SESSION_COOKIE_AGE}


def theme_preference(request):
    mode = UserThemePreference.Mode.AUTO
    accent = UserThemePreference.Accent.PURPLE

    if request.user.is_authenticated:
        try:
            preference = request.user.theme_preference
        except UserThemePreference.DoesNotExist:
            pass
        else:
            mode = preference.mode
            accent = preference.accent

    return {
        'theme_mode': mode,
        'theme_accent': accent,
    }
