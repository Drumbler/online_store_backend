from decimal import Decimal
from io import BytesIO
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from online_store_backend.orders.models import Order
from online_store_backend.orders.models import OrderItem
from online_store_backend.orders.models import OrderStatus
from online_store_backend.orders.models import ProductViewEvent


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="admin_reports",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )


def _create_order_item(order, product_id, title, unit_price, quantity):
    unit_price_dec = Decimal(str(unit_price))
    quantity_int = int(quantity)
    line_total = (unit_price_dec * quantity_int).quantize(Decimal("0.01"))
    return OrderItem.objects.create(
        order=order,
        product_id=product_id,
        product_title_snapshot=title,
        unit_price=unit_price_dec,
        unit_price_snapshot=unit_price_dec,
        unit_price_final=unit_price_dec,
        unit_price_original=unit_price_dec,
        quantity=quantity_int,
        line_total=line_total,
    )


def _create_view_event(product_id, viewed_at):
    event = ProductViewEvent.objects.create(product_id=product_id)
    ProductViewEvent.objects.filter(id=event.id).update(viewed_at=viewed_at)


def _seed_monthly_report_data():
    now = timezone.localtime(timezone.now())
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_point = period_start - timedelta(days=2)
    elapsed_days = max((now - period_start).days, 0)

    def _current_month_point(preferred_day_offset, seconds=0):
        candidate = period_start + timedelta(days=min(preferred_day_offset, elapsed_days), seconds=seconds)
        if candidate > now:
            return now
        return candidate

    paid_current = Order.objects.create(
        status=OrderStatus.PAID,
        total=Decimal("250.00"),
        paid_at=_current_month_point(2, seconds=10),
    )
    _create_order_item(paid_current, "p-1", "Товар A старый", Decimal("100.00"), 2)
    _create_order_item(paid_current, "p-2", "Товар B", Decimal("50.00"), 1)

    paid_without_paid_at = Order.objects.create(
        status=OrderStatus.PAID,
        total=Decimal("120.00"),
        paid_at=None,
    )
    Order.objects.filter(id=paid_without_paid_at.id).update(created_at=_current_month_point(4, seconds=20))
    paid_without_paid_at.refresh_from_db()
    _create_order_item(paid_without_paid_at, "p-1", "Товар A новый", Decimal("120.00"), 1)

    paid_previous_month = Order.objects.create(
        status=OrderStatus.PAID,
        total=Decimal("500.00"),
        paid_at=previous_month_point,
    )
    _create_order_item(paid_previous_month, "p-1", "Товар A прошлый месяц", Decimal("100.00"), 5)

    unpaid_current = Order.objects.create(
        status=OrderStatus.PENDING_PAYMENT,
        total=Decimal("990.00"),
    )
    _create_order_item(unpaid_current, "p-2", "Товар B неоплачен", Decimal("99.00"), 10)

    _create_view_event("p-1", _current_month_point(1, seconds=30))
    _create_view_event("p-1", _current_month_point(6, seconds=40))
    _create_view_event("p-2", _current_month_point(7, seconds=50))
    _create_view_event("p-3", _current_month_point(8, seconds=60))
    _create_view_event("p-2", previous_month_point)

    return period_start, now, previous_month_point


@pytest.mark.django_db
def test_track_view_endpoint_creates_event_for_guest(api_client):
    response = api_client.post("/api/products/doc-1/track-view/", {}, format="json")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert ProductViewEvent.objects.filter(product_id="doc-1").count() == 1


@pytest.mark.django_db
def test_admin_monthly_report_returns_expected_totals_and_rows(api_client, admin_user):
    period_start, now, _ = _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/admin/reports/monthly/")

    assert response.status_code == 200
    payload = response.json()

    assert payload["period"]["from"] == period_start.date().isoformat()
    assert payload["period"]["to"] == now.date().isoformat()

    assert payload["totals"] == {
        "views": 4,
        "units_sold": 4,
        "revenue": "370.00",
    }

    rows = {row["product_id"]: row for row in payload["results"]}
    assert rows["p-1"] == {
        "product_id": "p-1",
        "title": "Товар A новый",
        "views": 2,
        "units_sold": 3,
        "revenue": "320.00",
    }
    assert rows["p-2"] == {
        "product_id": "p-2",
        "title": "Товар B",
        "views": 1,
        "units_sold": 1,
        "revenue": "50.00",
    }
    assert rows["p-3"] == {
        "product_id": "p-3",
        "title": "p-3",
        "views": 1,
        "units_sold": 0,
        "revenue": "0.00",
    }


@pytest.mark.django_db
def test_admin_monthly_report_xlsx_has_totals_row_first(api_client, admin_user):
    load_workbook = pytest.importorskip("openpyxl").load_workbook

    _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/admin/reports/monthly.xlsx")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    workbook = load_workbook(filename=BytesIO(response.content))
    worksheet = workbook.active

    assert worksheet.cell(row=1, column=1).value == "ИТОГО"
    assert worksheet.cell(row=1, column=2).value == 4
    assert worksheet.cell(row=1, column=3).value == 4
    assert worksheet.cell(row=1, column=4).value == "370.00"

    assert worksheet.cell(row=2, column=1).value == "Название товара"
    assert worksheet.cell(row=2, column=2).value == "Просмотры"
    assert worksheet.cell(row=2, column=3).value == "Продано"
    assert worksheet.cell(row=2, column=4).value == "Выручка"


@pytest.mark.django_db
def test_admin_reports_periods_returns_only_recorded_months(api_client, admin_user):
    period_start, _, previous_month_point = _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/admin/reports/periods/")

    assert response.status_code == 200
    payload = response.json()
    current_year = period_start.year
    current_month = period_start.month
    previous_year = previous_month_point.year
    previous_month = previous_month_point.month

    assert current_year in payload["years"]
    assert current_month in payload["months_by_year"][str(current_year)]
    assert previous_year in payload["years"]
    assert previous_month in payload["months_by_year"][str(previous_year)]


@pytest.mark.django_db
def test_admin_monthly_report_accepts_year_and_month(api_client, admin_user):
    _, _, previous_month_point = _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(
        "/api/admin/reports/monthly/",
        {"year": previous_month_point.year, "month": previous_month_point.month},
    )

    assert response.status_code == 200
    payload = response.json()
    rows = {row["product_id"]: row for row in payload["results"]}
    assert payload["totals"]["views"] == 1
    assert payload["totals"]["units_sold"] == 5
    assert payload["totals"]["revenue"] == "500.00"
    assert rows["p-1"]["units_sold"] == 5
    assert rows["p-1"]["revenue"] == "500.00"
    assert rows["p-2"]["views"] == 1


@pytest.mark.django_db
def test_admin_yearly_report_returns_calendar_year_totals(api_client, admin_user):
    period_start, _, previous_month_point = _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/admin/reports/yearly/", {"year": period_start.year})

    assert response.status_code == 200
    payload = response.json()

    previous_month_in_current_year = previous_month_point.year == period_start.year
    expected_views = 4 + (1 if previous_month_in_current_year else 0)
    expected_units = 4 + (5 if previous_month_in_current_year else 0)
    expected_revenue = Decimal("370.00") + (Decimal("500.00") if previous_month_in_current_year else Decimal("0.00"))

    assert payload["period"]["from"] == f"{period_start.year}-01-01"
    assert payload["period"]["to"] == f"{period_start.year}-12-31"
    assert payload["totals"]["views"] == expected_views
    assert payload["totals"]["units_sold"] == expected_units
    assert payload["totals"]["revenue"] == format(expected_revenue, "f")


@pytest.mark.django_db
def test_yearly_report_xlsx_has_totals_row_first(api_client, admin_user):
    load_workbook = pytest.importorskip("openpyxl").load_workbook

    period_start, _, previous_month_point = _seed_monthly_report_data()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get("/api/admin/reports/yearly.xlsx", {"year": period_start.year})

    assert response.status_code == 200
    workbook = load_workbook(filename=BytesIO(response.content))
    worksheet = workbook.active

    previous_month_in_current_year = previous_month_point.year == period_start.year
    expected_views = 4 + (1 if previous_month_in_current_year else 0)
    expected_units = 4 + (5 if previous_month_in_current_year else 0)
    expected_revenue = Decimal("370.00") + (Decimal("500.00") if previous_month_in_current_year else Decimal("0.00"))

    assert worksheet.cell(row=1, column=1).value == "ИТОГО"
    assert worksheet.cell(row=1, column=2).value == expected_views
    assert worksheet.cell(row=1, column=3).value == expected_units
    assert worksheet.cell(row=1, column=4).value == format(expected_revenue, "f")


@pytest.mark.django_db
def test_reports_endpoints_require_admin_permissions(api_client):
    response_periods = api_client.get("/api/admin/reports/periods/")
    response_json = api_client.get("/api/admin/reports/monthly/")
    response_xlsx = api_client.get("/api/admin/reports/monthly.xlsx")
    response_yearly = api_client.get("/api/admin/reports/yearly/")
    response_yearly_xlsx = api_client.get("/api/admin/reports/yearly.xlsx")

    assert response_periods.status_code in {401, 403}
    assert response_json.status_code in {401, 403}
    assert response_xlsx.status_code in {401, 403}
    assert response_yearly.status_code in {401, 403}
    assert response_yearly_xlsx.status_code in {401, 403}
