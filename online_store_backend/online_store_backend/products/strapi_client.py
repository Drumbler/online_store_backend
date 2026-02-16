import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class StrapiUnavailableError(Exception):
    def __init__(self, message="Strapi unavailable"):
        super().__init__(message)


class StrapiNotFoundError(Exception):
    pass


class StrapiRequestError(Exception):
    def __init__(self, status_code, response_text):
        super().__init__(f"Strapi request failed with status {status_code}")
        self.status_code = status_code
        self.response_text = response_text


def _format_price(value) -> str:
    if value is None:
        return "0.00"
    try:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.warning("Invalid price value from Strapi: %r", value)
        return "0.00"
    return format(decimal_value, "f")


def _normalize_discount_percent(value) -> int:
    if value is None:
        return 0
    try:
        percent = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, percent))


def _apply_discount(price: str, discount_percent: int) -> str:
    if discount_percent <= 0:
        return price
    try:
        decimal_price = Decimal(str(price))
        discounted = (decimal_price * (Decimal("1") - Decimal(discount_percent) / Decimal("100"))).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, ValueError):
        return price
    return format(discounted, "f")


def _absolute_media_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = settings.STRAPI_PUBLIC_URL.rstrip("/") + "/"
    return urljoin(base, url.lstrip("/"))


def _extract_attributes(item):
    if not isinstance(item, dict):
        return {}
    if "attributes" in item and isinstance(item["attributes"], dict):
        merged = dict(item["attributes"])
        if "documentId" in item:
            merged["documentId"] = item["documentId"]
        if "id" in item and "id" not in merged:
            merged["id"] = item["id"]
        return merged
    return item


def _extract_image_url(image):
    if not image:
        return None
    if isinstance(image, str):
        return _absolute_media_url(image)
    if isinstance(image, list):
        if not image:
            return None
        return _extract_image_url(image[0])
    if not isinstance(image, dict):
        return None
    if "data" in image:
        image = image["data"]
        if image is None:
            return None
    attrs = _extract_attributes(image)
    if not attrs:
        return None
    url = attrs.get("url")
    if not url:
        return None
    return _absolute_media_url(url)


def _extract_thumbnail_url(image):
    if not image:
        return None
    if isinstance(image, list):
        if not image:
            return None
        return _extract_thumbnail_url(image[0])
    if not isinstance(image, dict):
        return None
    if "data" in image:
        image = image["data"]
        if image is None:
            return None
    attrs = _extract_attributes(image)
    if not attrs:
        return None
    formats = attrs.get("formats") or {}
    if not isinstance(formats, dict):
        return None
    thumbnail = formats.get("thumbnail")
    if not isinstance(thumbnail, dict):
        return None
    url = thumbnail.get("url")
    if not url:
        return None
    return _absolute_media_url(url)


def _normalize_category(category):
    if not category:
        return None
    if isinstance(category, dict) and "data" in category:
        category = category["data"]
        if category is None:
            return None
    attrs = _extract_attributes(category)
    if not attrs:
        return None
    category_id = attrs.get("documentId")
    if not category_id:
        return None
    return {
        "id": str(category_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
    }


def _normalize_product(item):
    attrs = _extract_attributes(item)
    document_id = attrs.get("documentId")
    if not document_id and isinstance(item, dict):
        document_id = item.get("documentId")
    if not document_id:
        logger.error("Product missing documentId: %r", item)
        return None
    discount_percent = _normalize_discount_percent(attrs.get("discount_percent"))
    price = _format_price(attrs.get("price"))
    discounted_price = _apply_discount(price, discount_percent) if discount_percent > 0 else None
    return {
        "id": str(document_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "price": price,
        "currency": "RUB",
        "image_url": _extract_image_url(attrs.get("image")),
        "thumbnail_url": _extract_thumbnail_url(attrs.get("image")),
        "category": _normalize_category(attrs.get("category")),
        "discount_percent": discount_percent,
        "discounted_price": discounted_price,
    }


def _normalize_category_admin(item):
    attrs = _extract_attributes(item)
    document_id = attrs.get("documentId")
    if not document_id and isinstance(item, dict):
        document_id = item.get("documentId")
    if not document_id:
        logger.error("Category missing documentId: %r", item)
        return None
    return {
        "id": str(document_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
    }


def _normalize_product_admin(item):
    attrs = _extract_attributes(item)
    document_id = attrs.get("documentId")
    if not document_id and isinstance(item, dict):
        document_id = item.get("documentId")
    if not document_id:
        logger.error("Product missing documentId: %r", item)
        return None
    discount_percent = _normalize_discount_percent(attrs.get("discount_percent"))
    return {
        "id": str(document_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "price": _format_price(attrs.get("price")),
        "currency": attrs.get("currency") or "RUB",
        "category": _normalize_category(attrs.get("category")),
        "discount_percent": discount_percent,
    }


def _get_read_token():
    token = settings.STRAPI_READ_API_TOKEN
    if not token:
        logger.error("STRAPI_READ_API_TOKEN is not configured.")
        raise StrapiUnavailableError("STRAPI_READ_API_TOKEN is not configured.")
    return token


def _get_admin_token():
    token = settings.STRAPI_ADMIN_API_TOKEN
    if not token:
        logger.error("STRAPI_ADMIN_API_TOKEN is not configured.")
        raise StrapiUnavailableError("STRAPI_ADMIN_API_TOKEN is not configured.")
    return token


def _strapi_request(method, path, *, params=None, json=None, token=None):
    base_url = settings.STRAPI_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=json,
            headers=headers,
            timeout=settings.STRAPI_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.exception("Strapi request failed: %s", exc)
        raise StrapiUnavailableError from exc
    if response.status_code == 404:
        raise StrapiNotFoundError
    if response.status_code >= 400:
        logger.error("Strapi returned %s: %s", response.status_code, response.text)
        raise StrapiRequestError(response.status_code, response.text)
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        logger.exception("Invalid JSON from Strapi: %s", exc)
        raise StrapiUnavailableError from exc


def _strapi_get(path, params=None):
    return _strapi_request("GET", path, params=params)


def _strapi_get_public(path, params=None):
    return _strapi_request("GET", path, params=params, token=_get_read_token())


def _strapi_get_admin(path, params=None):
    return _strapi_request("GET", path, params=params, token=_get_admin_token())


def list_products(*, page: int, page_size: int, params=None):
    params = params or {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
        "populate[0]": "image",
        "populate[1]": "category",
    }
    try:
        payload = _strapi_get_public("/api/products", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    items = payload.get("data", []) if isinstance(payload, dict) else []
    results = []
    for item in items:
        normalized = _normalize_product(item)
        if normalized:
            results.append(normalized)
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": len(results),
    }
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    meta_pagination = meta.get("pagination") if isinstance(meta, dict) else None
    if isinstance(meta_pagination, dict):
        pagination["page"] = meta_pagination.get("page", pagination["page"])
        pagination["page_size"] = meta_pagination.get("pageSize", pagination["page_size"])
        pagination["total"] = meta_pagination.get("total", pagination["total"])
    return results, pagination


def get_product(document_id: str):
    params = {
        "populate[0]": "image",
        "populate[1]": "category",
    }
    try:
        payload = _strapi_get_public(f"/api/products/{document_id}", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    normalized = _normalize_product(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def get_product_by_slug(slug: str):
    params = {
        "filters[slug][$eq]": slug,
        "populate[0]": "image",
        "populate[1]": "category",
    }
    try:
        payload = _strapi_get_public("/api/products", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    items = payload.get("data", []) if isinstance(payload, dict) else []
    if not items:
        raise StrapiNotFoundError
    normalized = _normalize_product(items[0])
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def list_categories(*, page: int, page_size: int):
    params = {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
    }
    try:
        payload = _strapi_get_public("/api/categories", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    items = payload.get("data", []) if isinstance(payload, dict) else []
    results = []
    for item in items:
        normalized = _normalize_category_admin(item)
        if normalized:
            results.append(normalized)
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": len(results),
    }
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    meta_pagination = meta.get("pagination") if isinstance(meta, dict) else None
    if isinstance(meta_pagination, dict):
        pagination["page"] = meta_pagination.get("page", pagination["page"])
        pagination["page_size"] = meta_pagination.get("pageSize", pagination["page_size"])
        pagination["total"] = meta_pagination.get("total", pagination["total"])
    return results, pagination


def get_category(document_id: str):
    try:
        payload = _strapi_get_public(f"/api/categories/{document_id}")
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    normalized = _normalize_category_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def list_categories_admin(*, page: int, page_size: int):
    params = {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
    }
    try:
        payload = _strapi_get_admin("/api/categories", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    items = payload.get("data", []) if isinstance(payload, dict) else []
    results = []
    for item in items:
        normalized = _normalize_category_admin(item)
        if normalized:
            results.append(normalized)
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": len(results),
    }
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    meta_pagination = meta.get("pagination") if isinstance(meta, dict) else None
    if isinstance(meta_pagination, dict):
        pagination["page"] = meta_pagination.get("page", pagination["page"])
        pagination["page_size"] = meta_pagination.get("pageSize", pagination["page_size"])
        pagination["total"] = meta_pagination.get("total", pagination["total"])
    return results, pagination


def get_category_admin(document_id: str):
    try:
        payload = _strapi_get_admin(f"/api/categories/{document_id}")
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    normalized = _normalize_category_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def create_category_admin(data):
    payload = _strapi_request(
        "POST",
        "/api/categories",
        json={"data": data},
        token=_get_admin_token(),
    )
    item = payload.get("data") if isinstance(payload, dict) else payload
    normalized = _normalize_category_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def update_category_admin(document_id: str, data):
    payload = _strapi_request(
        "PUT",
        f"/api/categories/{document_id}",
        json={"data": data},
        token=_get_admin_token(),
    )
    item = payload.get("data") if isinstance(payload, dict) else payload
    normalized = _normalize_category_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def delete_category_admin(document_id: str):
    try:
        _strapi_request(
            "DELETE",
            f"/api/categories/{document_id}",
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc


def list_products_admin(*, page: int, page_size: int, params=None):
    params = params or {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
        "populate": "category",
    }
    try:
        payload = _strapi_get_admin("/api/products", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    items = payload.get("data", []) if isinstance(payload, dict) else []
    results = []
    for item in items:
        normalized = _normalize_product_admin(item)
        if normalized:
            results.append(normalized)
    pagination = {
        "page": page,
        "page_size": page_size,
        "total": len(results),
    }
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    meta_pagination = meta.get("pagination") if isinstance(meta, dict) else None
    if isinstance(meta_pagination, dict):
        pagination["page"] = meta_pagination.get("page", pagination["page"])
        pagination["page_size"] = meta_pagination.get("pageSize", pagination["page_size"])
        pagination["total"] = meta_pagination.get("total", pagination["total"])
    return results, pagination


def get_product_admin(document_id: str):
    params = {"populate": "category"}
    try:
        payload = _strapi_get_admin(f"/api/products/{document_id}", params=params)
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    normalized = _normalize_product_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def create_product_admin(data):
    payload = _strapi_request(
        "POST",
        "/api/products",
        json={"data": data},
        token=_get_admin_token(),
    )
    item = payload.get("data") if isinstance(payload, dict) else payload
    normalized = _normalize_product_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def update_product_admin(document_id: str, data):
    payload = _strapi_request(
        "PUT",
        f"/api/products/{document_id}",
        json={"data": data},
        token=_get_admin_token(),
    )
    item = payload.get("data") if isinstance(payload, dict) else payload
    normalized = _normalize_product_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def update_product_admin_flat(document_id: str, data):
    try:
        payload = _strapi_request(
            "PUT",
            f"/api/products/{document_id}",
            json=data,
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        response_text = exc.response_text or ""
        if exc.status_code == 400 or "missing \"data\"" in response_text.lower():
            payload = _strapi_request(
                "PUT",
                f"/api/products/{document_id}",
                json={"data": data},
                token=_get_admin_token(),
            )
        else:
            raise exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    normalized = _normalize_product_admin(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized


def delete_product_admin(document_id: str):
    try:
        _strapi_request(
            "DELETE",
            f"/api/products/{document_id}",
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc


def get_product_admin_raw(document_id: str):
    params = {"populate": "category"}
    try:
        payload = _strapi_get_admin(f"/api/products/{document_id}", params=params)
    except StrapiRequestError as exc:
        raise exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    attrs = _extract_attributes(item)
    if not attrs:
        raise StrapiUnavailableError
    return attrs


def update_product_admin_raw(document_id: str, data):
    try:
        _strapi_request(
            "PUT",
            f"/api/products/{document_id}",
            json={"data": data},
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise exc
