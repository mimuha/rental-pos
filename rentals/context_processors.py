from django.conf import settings

from .models import UserThemePreference

THEME_SESSION_KEY = 'theme_preference'


def session_timeout(request):
    return {'SESSION_TIMEOUT': settings.SESSION_COOKIE_AGE}


def theme_preference(request):
    mode = UserThemePreference.Mode.AUTO
    accent = UserThemePreference.Accent.PURPLE

    if request.user.is_authenticated:
        session = getattr(request, 'session', None)
        # Simpan hasil di sesi supaya tidak query ulang di setiap request.
        cached = session.get(THEME_SESSION_KEY) if session is not None else None
        if isinstance(cached, dict) and cached.get('mode') and cached.get('accent'):
            mode = cached['mode']
            accent = cached['accent']
        else:
            try:
                preference = request.user.theme_preference
            except UserThemePreference.DoesNotExist:
                pass
            else:
                mode = preference.mode
                accent = preference.accent
            if session is not None:
                session[THEME_SESSION_KEY] = {'mode': mode, 'accent': accent}

    return {
        'theme_mode': mode,
        'theme_accent': accent,
    }
