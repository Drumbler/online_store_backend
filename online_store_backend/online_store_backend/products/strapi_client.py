"""Клиент для взаимодействия с Strapi Catalog API."""

import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class StrapiUnavailableError(Exception):
    """Ошибка недоступности Strapi или некорректного ответа."""

    def __init__(self, message="Strapi unavailable"):
        super().__init__(message)


class StrapiNotFoundError(Exception):
    """Ошибка отсутствия сущности в Strapi."""

    pass


class StrapiRequestError(Exception):
    """Ошибка HTTP-запроса к Strapi с сохранением статуса и тела ответа."""

    def __init__(self, status_code, response_text):
        super().__init__(f"Strapi request failed with status {status_code}")
        self.status_code = status_code
        self.response_text = response_text


def _format_price(value) -> str:
    """Нормализует цену к строке с двумя знаками после запятой."""
    if value is None:
        return "0.00"
    try:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.warning("Invalid price value from Strapi: %r", value)
        return "0.00"
    return format(decimal_value, "f")


def _normalize_discount_percent(value) -> int:
    """Приводит скидку к целому значению в диапазоне 0..100."""
    if value is None:
        return 0
    try:
        percent = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, percent))


def _apply_discount(price: str, discount_percent: int) -> str:
    """Применяет процентную скидку к цене."""
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
    """Преобразует относительный URL медиа в абсолютный."""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = settings.STRAPI_PUBLIC_URL.rstrip("/") + "/"
    return urljoin(base, url.lstrip("/"))


def _extract_attributes(item):
    """Извлекает `attributes` из формата ответа Strapi."""
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


def _iter_media_attributes(image):
    """Нормализует медиа-данные к списку словарей атрибутов."""
    if not image:
        return []
    if isinstance(image, str):
        return [{"url": image}]
    if isinstance(image, dict) and "data" in image:
        image = image["data"]
    if image is None:
        return []
    items = image if isinstance(image, list) else [image]
    normalized = []
    for item in items:
        if isinstance(item, str):
            normalized.append({"url": item})
            continue
        attrs = _extract_attributes(item)
        if attrs:
            normalized.append(attrs)
    return normalized


def _extract_gallery_urls(image):
    """Возвращает уникальные абсолютные URL изображений галереи."""
    urls = []
    seen = set()
    for attrs in _iter_media_attributes(image):
        url = attrs.get("url")
        if not url:
            continue
        absolute = _absolute_media_url(url)
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def _extract_image_url(image):
    """Возвращает URL основного изображения."""
    gallery = _extract_gallery_urls(image)
    return gallery[0] if gallery else None


def _extract_thumbnail_url(image):
    """Возвращает URL thumbnail-версии изображения, если она доступна."""
    for attrs in _iter_media_attributes(image):
        formats = attrs.get("formats") or {}
        if not isinstance(formats, dict):
            continue
        thumbnail = formats.get("thumbnail")
        if not isinstance(thumbnail, dict):
            continue
        url = thumbnail.get("url")
        if not url:
            continue
        return _absolute_media_url(url)
    return None


def _extract_media_id(image):
    """Возвращает numeric id первого медиа-элемента, если доступен."""
    for attrs in _iter_media_attributes(image):
        candidate = attrs.get("id")
        if candidate in (None, ""):
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _normalize_category(category):
    """Нормализует категорию к единому публичному формату."""
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
    """Нормализует товар Strapi к публичному контракту API."""
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
    gallery_urls = _extract_gallery_urls(attrs.get("image"))
    return {
        "id": str(document_id),
        "slug": attrs.get("slug"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "price": price,
        "currency": "RUB",
        "image_url": _extract_image_url(attrs.get("image")),
        "thumbnail_url": _extract_thumbnail_url(attrs.get("image")),
        "gallery_urls": gallery_urls,
        "category": _normalize_category(attrs.get("category")),
        "discount_percent": discount_percent,
        "discounted_price": discounted_price,
    }


def _normalize_category_admin(item):
    """Нормализует категорию к формату админского API."""
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
    """Нормализует товар к формату админского API."""
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
        "publish": bool(attrs.get("publishedAt")),
        "image_id": _extract_media_id(attrs.get("image")),
        "image_url": _extract_image_url(attrs.get("image")),
    }


def _get_read_token():
    """Возвращает read-only API токен Strapi."""
    token = settings.STRAPI_READ_API_TOKEN
    if not token:
        logger.error("STRAPI_READ_API_TOKEN is not configured.")
        raise StrapiUnavailableError("STRAPI_READ_API_TOKEN is not configured.")
    return token


def _get_admin_token():
    """Возвращает admin API токен Strapi."""
    token = settings.STRAPI_ADMIN_API_TOKEN
    if not token:
        logger.error("STRAPI_ADMIN_API_TOKEN is not configured.")
        raise StrapiUnavailableError("STRAPI_ADMIN_API_TOKEN is not configured.")
    return token


def _strapi_request(method, path, *, params=None, json=None, data=None, files=None, token=None):
    """Выполняет HTTP-запрос к Strapi и обрабатывает типовые ошибки."""
    base_url = settings.STRAPI_BASE_URL.rstrip("/")
    url = f"{base_url}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request_kwargs = {
        "method": method,
        "url": url,
        "params": params,
        "headers": headers,
        "timeout": settings.STRAPI_TIMEOUT_SECONDS,
    }
    if files is not None:
        request_kwargs["files"] = files
        if data is not None:
            request_kwargs["data"] = data
    else:
        request_kwargs["json"] = json
    try:
        response = requests.request(**request_kwargs)
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
    """Упрощенный GET-запрос к Strapi без токена."""
    return _strapi_request("GET", path, params=params)


def _strapi_get_public(path, params=None):
    """GET-запрос к Strapi с read-токеном."""
    return _strapi_request("GET", path, params=params, token=_get_read_token())


def _strapi_get_admin(path, params=None):
    """GET-запрос к Strapi с admin-токеном."""
    return _strapi_request("GET", path, params=params, token=_get_admin_token())


def _normalize_upload_response(payload):
    """Нормализует ответ /api/upload к объекту {id, url, name}."""
    item = None
    if isinstance(payload, list) and payload:
        item = payload[0]
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data

    if not isinstance(item, dict):
        return None

    attrs = _extract_attributes(item)
    file_id = attrs.get("id")
    url = attrs.get("url")
    if file_id in (None, "") or not url:
        return None

    try:
        numeric_id = int(file_id)
    except (TypeError, ValueError):
        return None

    return {
        "id": numeric_id,
        "url": _absolute_media_url(str(url)),
        "name": attrs.get("name"),
    }


def upload_product_image_admin(file_name: str, file_content: bytes, content_type: str | None = None):
    """Загружает файл изображения в Strapi и возвращает id/url загруженного медиа."""
    payload = _strapi_request(
        "POST",
        "/api/upload",
        files={"files": (file_name, file_content, content_type or "application/octet-stream")},
        token=_get_admin_token(),
    )
    normalized = _normalize_upload_response(payload)
    if not normalized:
        raise StrapiUnavailableError("Invalid upload response from Strapi.")
    return normalized


def list_products(*, page: int, page_size: int, params=None):
    """Возвращает список публичных товаров и пагинацию."""
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
    """Возвращает публичные данные товара по documentId."""
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
    """Возвращает товар по slug."""
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
    """Возвращает публичный список категорий и пагинацию."""
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
    """Возвращает категорию по documentId."""
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
    """Возвращает список категорий через admin API Strapi."""
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
    """Возвращает категорию из admin API по documentId."""
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
    """Создает категорию через admin API Strapi."""
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
    """Обновляет категорию через admin API Strapi."""
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
    """Удаляет категорию через admin API Strapi."""
    try:
        _strapi_request(
            "DELETE",
            f"/api/categories/{document_id}",
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc


def list_products_admin(*, page: int, page_size: int, params=None):
    """Возвращает список товаров через admin API Strapi."""
    params = params or {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
        "populate[0]": "category",
        "populate[1]": "image",
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
    """Возвращает товар через admin API Strapi."""
    params = {
        "populate[0]": "category",
        "populate[1]": "image",
    }
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
    """Создает товар через admin API Strapi."""
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
    """Обновляет товар через admin API Strapi."""
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
    """Обновляет товар с fallback между flat- и nested-payload форматами."""
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
    """Удаляет товар через admin API Strapi."""
    try:
        _strapi_request(
            "DELETE",
            f"/api/products/{document_id}",
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise StrapiUnavailableError from exc


def get_product_admin_raw(document_id: str):
    """Возвращает сырой словарь атрибутов товара из Strapi."""
    params = {
        "populate[0]": "category",
        "populate[1]": "image",
    }
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
    """Отправляет сырой payload обновления товара в Strapi."""
    try:
        _strapi_request(
            "PUT",
            f"/api/products/{document_id}",
            json={"data": data},
            token=_get_admin_token(),
        )
    except StrapiRequestError as exc:
        raise exc
