import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class StrapiUnavailableError(Exception):
    pass


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


def _absolute_media_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = settings.STRAPI_BASE_URL.rstrip("/") + "/"
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
    return {
        "id": str(document_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "price": _format_price(attrs.get("price")),
        "currency": "RUB",
        "image_url": _extract_image_url(attrs.get("image")),
        "category": _normalize_category(attrs.get("category")),
    }


def _strapi_get(path, params=None):
    base_url = settings.STRAPI_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    try:
        response = requests.get(url, params=params, timeout=settings.STRAPI_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.exception("Strapi request failed: %s", exc)
        raise StrapiUnavailableError from exc
    if response.status_code == 404:
        raise StrapiNotFoundError
    if response.status_code >= 400:
        logger.error("Strapi returned %s: %s", response.status_code, response.text)
        raise StrapiRequestError(response.status_code, response.text)
    try:
        return response.json()
    except ValueError as exc:
        logger.exception("Invalid JSON from Strapi: %s", exc)
        raise StrapiUnavailableError from exc


def list_products(*, page: int, page_size: int):
    params = {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
        "populate": "category",
        "populate[image]": "true",
    }
    try:
        payload = _strapi_get("/api/products", params=params)
    except StrapiRequestError as exc:
        if exc.status_code == 400:
            logger.warning("Strapi rejected image populate, retrying without image.")
            params.pop("populate[image]", None)
            try:
                payload = _strapi_get("/api/products", params=params)
            except StrapiRequestError as retry_exc:
                raise StrapiUnavailableError from retry_exc
        else:
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
        "populate": "category",
        "populate[image]": "true",
    }
    try:
        payload = _strapi_get(f"/api/products/{document_id}", params=params)
    except StrapiRequestError as exc:
        if exc.status_code == 400:
            logger.warning("Strapi rejected image populate, retrying without image.")
            params.pop("populate[image]", None)
            try:
                payload = _strapi_get(f"/api/products/{document_id}", params=params)
            except StrapiRequestError as retry_exc:
                raise StrapiUnavailableError from retry_exc
        else:
            raise StrapiUnavailableError from exc
    item = payload.get("data") if isinstance(payload, dict) else payload
    if item is None:
        raise StrapiNotFoundError
    normalized = _normalize_product(item)
    if not normalized:
        raise StrapiUnavailableError
    return normalized
