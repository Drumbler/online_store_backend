from decimal import Decimal
from decimal import InvalidOperation
from decimal import ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def clamp_discount_percent(discount_percent: int | float | Decimal | None) -> int:
    try:
        value = int(Decimal(str(discount_percent or 0)))
    except (InvalidOperation, TypeError, ValueError):
        value = 0
    return max(0, min(100, value))


def compute_discounted_unit_price(price: Decimal, discount_percent: int | float | Decimal) -> Decimal:
    safe_price = _quantize_money(Decimal(str(price)))
    safe_discount = clamp_discount_percent(discount_percent)
    if safe_discount <= 0:
        return safe_price
    factor = Decimal("1") - (Decimal(safe_discount) / Decimal("100"))
    return _quantize_money(safe_price * factor)


def compute_line_total(unit_price: Decimal, qty: int) -> Decimal:
    return _quantize_money(Decimal(str(unit_price)) * Decimal(int(qty)))
