import logging

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .services import ensure_shop_appearance_initialized

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def init_shop_appearance_defaults(sender, **kwargs):
    if sender.label != "appearance":
        return
    try:
        ensure_shop_appearance_initialized()
    except Exception:  # pragma: no cover - defensive logging only
        logger.exception("Failed to initialize shop appearance defaults after migrate.")
