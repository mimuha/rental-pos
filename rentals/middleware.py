import ipaddress
import time

from django.conf import settings
from django.http import HttpResponse

from .cache_utils import safe_cache_delete, safe_cache_get, safe_cache_set


class LoginRateLimitMiddleware:
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 900
    BLOCK_DURATION = 1800

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path == '/admin/login/':
            ip = self._client_ip(request)
            cache_key = f'admin_login_attempts_{ip}'
            block_key = f'admin_login_blocked_{ip}'

            if safe_cache_get(block_key):
                return HttpResponse(
                    'Terlalu banyak percobaan login. Silakan coba lagi dalam 30 menit.',
                    status=429,
                    content_type='text/plain',
                )

            response = self.get_response(request)

            if response.status_code == 302 and response.get('Location', '').endswith('/admin/'):
                safe_cache_delete(cache_key)
                safe_cache_delete(block_key)
            else:
                attempts = safe_cache_get(cache_key, 0) + 1
                safe_cache_set(cache_key, attempts, self.WINDOW_SECONDS)

                if attempts >= self.MAX_ATTEMPTS:
                    safe_cache_set(block_key, int(time.time()), self.BLOCK_DURATION)

            return response

        return self.get_response(request)

    @staticmethod
    def _client_ip(request):
        remote_addr = request.META.get('REMOTE_ADDR', '')
        trusted_proxies = getattr(settings, 'TRUSTED_PROXY_COUNT', 0)

        if trusted_proxies <= 0:
            return remote_addr

        x_forwarded = request.headers.get('X-Forwarded-For', '')
        if not x_forwarded:
            return remote_addr

        parts = [part.strip() for part in x_forwarded.split(',') if part.strip()]
        if len(parts) < trusted_proxies:
            return remote_addr

        candidate = parts[-trusted_proxies]
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            return remote_addr
