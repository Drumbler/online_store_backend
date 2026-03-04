"""Utilities for versioned product-response cache keys."""

from django.core.cache import cache

PRODUCTS_CACHE_VERSION_KEY = "products:cache:version"
DEFAULT_PRODUCTS_CACHE_VERSION = 1


def get_products_cache_version() -> int:
    """Returns current cache version for product list/detail endpoints."""
    raw_value = cache.get(PRODUCTS_CACHE_VERSION_KEY, DEFAULT_PRODUCTS_CACHE_VERSION)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_PRODUCTS_CACHE_VERSION
    if value < 1:
        value = DEFAULT_PRODUCTS_CACHE_VERSION
    return value


def bump_products_cache_version() -> int:
    """Bumps cache version to invalidate all previously cached product payloads."""
    try:
        return int(cache.incr(PRODUCTS_CACHE_VERSION_KEY))
    except (ValueError, TypeError, AttributeError):
        next_value = get_products_cache_version() + 1
        cache.set(PRODUCTS_CACHE_VERSION_KEY, next_value, timeout=None)
        return next_value
