"""
redis_cache.py
Shared Redis client and simple cache decorator.
"""
import json
import functools
import hashlib
import ssl
import structlog
from typing import Any, Callable, Optional
from app.config import settings

log = structlog.get_logger(__name__)

_redis_client = None


def _make_redis_client(url: str, **kwargs):
    """
    Build a Redis client from a URL, correctly handling SSL for rediss:// URLs.

    redis-py 4.2+ requires ssl_cert_reqs to be the ssl.CERT_NONE enum constant,
    not the string "CERT_NONE".  Passing ssl_cert_reqs=ssl.CERT_NONE explicitly
    avoids the `Invalid SSL Certificate Requirements Flag: CERT_NONE` error that
    occurs when connecting to Upstash or other managed Redis services via TLS.
    """
    import redis as redis_lib
    if url.startswith("rediss://"):
        kwargs.setdefault("ssl_cert_reqs", ssl.CERT_NONE)
    return redis_lib.from_url(url, **kwargs)


def get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = _make_redis_client(settings.redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:
            log.warning("redis_cache.connect_failed", error=str(e))
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    if not r:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception:
        return False


def cache_delete(key: str) -> bool:
    r = get_redis()
    if not r:
        return False
    try:
        r.delete(key)
        return True
    except Exception:
        return False


def cached(prefix: str, ttl: int = 3600):
    """
    Decorator that caches function result in Redis.
    Cache key: {prefix}:{hash(args + kwargs)}
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw = f"{args}{kwargs}"
            key = f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"
            cached_val = cache_get(key)
            if cached_val is not None:
                return cached_val
            result = fn(*args, **kwargs)
            cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator