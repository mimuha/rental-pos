import time
from django.core.cache import cache
from django.http import HttpResponse


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

            if cache.get(block_key):
                return HttpResponse(
                    'Terlalu banyak percobaan login. Silakan coba lagi dalam 30 menit.',
                    status=429,
                    content_type='text/plain',
                )

            response = self.get_response(request)

            if response.status_code == 302 and response.get('Location', '').endswith('/admin/'):
                cache.delete(cache_key)
                cache.delete(block_key)
            else:
                attempts = cache.get(cache_key, 0) + 1
                cache.set(cache_key, attempts, self.WINDOW_SECONDS)

                if attempts >= self.MAX_ATTEMPTS:
                    cache.set(block_key, int(time.time()), self.BLOCK_DURATION)

            return response

        return self.get_response(request)

    @staticmethod
    def _client_ip(request):
        x_forwarded = request.headers.get('X-Forwarded-For', '')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
