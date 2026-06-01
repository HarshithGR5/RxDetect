"""
redis_cache.py
Shared Redis connection pool + simple cache helpers.

Upstash optimization notes
--------------------------
Upstash charges per command, not per connection time.  The two biggest idle
consumers are:
  1. Multiple connection pools (openfda/rxnorm each created their own) —
     each reconnect sends AUTH + SELECT commands.
  2. Celery result backend accumulating keys (now fixed with result_expires).

This module now maintains ONE shared ConnectionPool.  All callers (openfda,
rxnorm, etc.) import get_redis() from here instead of calling from_url() or
_make_redis_client() themselves.
"""
import json
import functools
import hashlib
import ssl
import structlog
from typing import Any, Callable, Optional
from app.config import settings

log = structlog.get_logger(__name__)

_pool = None
_redis_client = None


def _build_pool(url: str):
    """
    Build a ConnectionPool from a Redis URL with correct TLS handling.

    WHY we don't use redis.from_url() for rediss:// URLs
    -----------------------------------------------------
    Upstash encodes ssl_cert_reqs=CERT_NONE in the URL query string.
    redis-py 4.2+ rejects the uppercase form with RedisError.
    We parse the URL manually and pass ssl_cert_reqs=ssl.CERT_NONE (int enum).

    Idle-optimization settings
    --------------------------
    - max_connections=5  : limits pool size; Upstash free tier allows 100
      simultaneous connections but we don't need many.
    - socket_connect_timeout=3 : fail fast if Upstash is unreachable.
    - socket_timeout=3        : don't hang on slow commands.
    - health_check_interval=0 : redis-py's background health-check pings are
      disabled — they fire even with no traffic and cost commands on Upstash.
    """
    import redis as redis_lib
    from redis import ConnectionPool, SSLConnection, Connection
    from urllib.parse import urlparse

    if not url.startswith("rediss://"):
        return ConnectionPool.from_url(
            url,
            decode_responses=True,
            max_connections=5,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=0,
        )

    parsed = urlparse(url)
    db = 0
    try:
        db = int((parsed.path or "/0").lstrip("/") or 0)
    except ValueError:
        pass

    return ConnectionPool(
        connection_class=SSLConnection,
        host=parsed.hostname,
        port=parsed.port or 6379,
        username=parsed.username or "default",
        password=parsed.password,
        db=db,
        decode_responses=True,
        max_connections=5,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=0,
        ssl_cert_reqs=ssl.CERT_NONE,
    )


def get_redis():
    """Return the shared Redis client, creating it lazily on first call."""
    global _pool, _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        if _pool is None:
            _pool = _build_pool(settings.redis_url)
        _redis_client = redis_lib.Redis(connection_pool=_pool)
        _redis_client.ping()
        log.info("redis_cache.connected")
    except Exception as e:
        log.warning("redis_cache.connect_failed", error=str(e))
        _pool = None
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
