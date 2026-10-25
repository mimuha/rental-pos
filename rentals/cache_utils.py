"""Akses cache yang tidak boleh menjatuhkan halaman.

Sejak Django 6 backend Redis tidak lagi punya opsi ``IGNORE_EXCEPTIONS``:
kegagalan koneksi (Upstash down, kuota habis, token salah) akan dilempar ke
view dan menjadi HTTP 500. Helper di sini menelan error tersebut dan
mengembalikan nilai default supaya cache bersifat best-effort:

- dashboard hanya menghitung ulang tanpa cache,
- rate-limit login menjadi fail-open (tidak memblokir siapa pun),
- sesi tetap aman karena disimpan di database (bukan ``cached_db``).
"""

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)


def safe_cache_get(key, default=None):
    try:
        return cache.get(key, default)
    except Exception:
        logger.warning(
            'Cache get gagal untuk key %r; lanjut tanpa cache.',
            key,
            exc_info=True,
        )
        return default


def safe_cache_set(key, value, timeout=None):
    try:
        cache.set(key, value, timeout)
        return True
    except Exception:
        logger.warning(
            'Cache set gagal untuk key %r; nilai tidak di-cache.',
            key,
            exc_info=True,
        )
        return False


def safe_cache_delete(key):
    try:
        cache.delete(key)
        return True
    except Exception:
        logger.warning(
            'Cache delete gagal untuk key %r.',
            key,
            exc_info=True,
        )
        return False
