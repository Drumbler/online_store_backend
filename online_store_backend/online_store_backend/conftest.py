"""Глобальные pytest-фикстуры для backend-тестов."""

import pytest

from online_store_backend.users.models import User
from online_store_backend.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    """Подменяет MEDIA_ROOT на временную директорию в тестах."""
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    """Возвращает тестового пользователя через фабрику."""
    return UserFactory()
