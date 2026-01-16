from .models import Cart
from .models import CartItem
from .models import CartStatus


def _ensure_session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _merge_cart_items(target_cart: Cart, source_cart: Cart) -> None:
    existing = {item.product_id: item for item in target_cart.items.all()}
    for item in source_cart.items.all():
        current = existing.get(item.product_id)
        if current:
            current.quantity += item.quantity
            current.product_title_snapshot = item.product_title_snapshot
            current.unit_price_snapshot = item.unit_price_snapshot
            current.currency_snapshot = item.currency_snapshot
            current.image_url_snapshot = item.image_url_snapshot
            current.save(
                update_fields=[
                    "quantity",
                    "product_title_snapshot",
                    "unit_price_snapshot",
                    "currency_snapshot",
                    "image_url_snapshot",
                    "updated_at",
                ]
            )
        else:
            CartItem.objects.create(
                cart=target_cart,
                product_id=item.product_id,
                product_title_snapshot=item.product_title_snapshot,
                unit_price_snapshot=item.unit_price_snapshot,
                currency_snapshot=item.currency_snapshot,
                image_url_snapshot=item.image_url_snapshot,
                quantity=item.quantity,
            )


def get_active_cart(request):
    session_key = _ensure_session_key(request)
    if request.user.is_authenticated:
        user_cart = (
            Cart.objects.filter(user=request.user, status=CartStatus.ACTIVE)
            .prefetch_related("items")
            .first()
        )
        session_cart = (
            Cart.objects.filter(session_key=session_key, status=CartStatus.ACTIVE)
            .prefetch_related("items")
            .first()
        )
        if session_cart and user_cart and session_cart.pk == user_cart.pk:
            return user_cart
        if session_cart and user_cart:
            _merge_cart_items(user_cart, session_cart)
            session_cart.status = CartStatus.CHECKED_OUT
            session_cart.session_key = None
            session_cart.save(update_fields=["status", "session_key", "updated_at"])
            session_cart.items.all().delete()
            return user_cart
        if session_cart and not user_cart:
            session_cart.user = request.user
            session_cart.session_key = None
            session_cart.save(update_fields=["user", "session_key", "updated_at"])
            return session_cart
        if user_cart:
            return user_cart
        return Cart.objects.create(user=request.user, status=CartStatus.ACTIVE)

    cart, _ = Cart.objects.get_or_create(
        session_key=session_key,
        status=CartStatus.ACTIVE,
        defaults={"user": None},
    )
    return cart


def get_or_create_cart(request) -> Cart:
    return get_active_cart(request)
