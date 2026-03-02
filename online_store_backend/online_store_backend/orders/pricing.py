"""Утилиты расчета цен, скидок и итогов по позициям заказа."""

from decimal import Decimal
from decimal import InvalidOperation
from decimal import ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


def _quantize_money(value: Decimal) -> Decimal:
    """Округлить денежное значение до 2 знаков после запятой."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def clamp_discount_percent(discount_percent: int | float | Decimal | None) -> int:
    """Нормализовать скидку к целому проценту в диапазоне 0..100."""
    try:
        value = int(Decimal(str(discount_percent or 0)))
    except (InvalidOperation, TypeError, ValueError):
        value = 0
    return max(0, min(100, value))


def compute_discounted_unit_price(price: Decimal, discount_percent: int | float | Decimal) -> Decimal:
    """Посчитать цену за единицу с учетом скидки."""
    safe_price = _quantize_money(Decimal(str(price)))
    safe_discount = clamp_discount_percent(discount_percent)
    if safe_discount <= 0:
        return safe_price
    factor = Decimal("1") - (Decimal(safe_discount) / Decimal("100"))
    return _quantize_money(safe_price * factor)


def compute_line_total(unit_price: Decimal, qty: int) -> Decimal:
    """Посчитать итог позиции: цена за единицу * количество."""
    return _quantize_money(Decimal(str(unit_price)) * Decimal(int(qty)))
